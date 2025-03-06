"""
Bids API Blueprint - Handles bid placement functionality

This module provides the following endpoints:
- POST /api/bids/ - Place a bid on an auction
"""
from flask import Blueprint, request, jsonify
from extensions import db
from models import Bid, Auction, Wallet, User
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN, InvalidOperation
import logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from routes.winners import recalc_bid_uniqueness

bids_bp = Blueprint('bids', __name__)

@bids_bp.route('/', methods=['POST'])
@jwt_required()
def place_bid():
    """
    Place a bid on an auction
    Returns:
        Bid confirmation including updated wallet balance and winner status
    """
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ('auctionId', 'amount')):
            return jsonify({"message": "Missing required fields"}), 400

        user_id = get_jwt_identity()
        amount = float(data['amount'])
        auction_id = int(data['auctionId'])

        logging.info(f"Placing bid: User {user_id}, Amount {amount}, Auction {auction_id}")

        # BID VALIDATION
        if amount <= 0:
            return jsonify({"message": "Bid amount must be positive"}), 400

        # GET WALLET
        wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            return jsonify({"message": "Wallet not found"}), 404

        logging.info(f"Current wallet balance: {wallet.balance}")
        
        # CHECK FUNDS
        if wallet.balance < amount:
            return jsonify({"message": "Insufficient funds in wallet"}), 400

        # GET AUCTION AND STATUS
        auction = Auction.query.get(auction_id)
        if not auction:
            return jsonify({"message": "Auction not found"}), 404

        current_time = datetime.now(timezone.utc)
        expires_at = auction.expires_at.replace(tzinfo=timezone.utc) if auction.expires_at.tzinfo is None else auction.expires_at

        if current_time > expires_at:
            auction.status = 'expired'
            db.session.commit()
            return jsonify({"message": "Auction has expired"}), 400

        if auction.status != 'active':
            return jsonify({"message": "Auction is not active"}), 400

        # VALIDATE BID AMOUNT (AT MOST ONE DECIMAL)
        try:
            amount_decimal = Decimal(str(amount))
            if amount_decimal % 1 != 0:
                rounded = amount_decimal.quantize(Decimal('0.1'), rounding=ROUND_DOWN)
                if amount_decimal != rounded:
                    return jsonify({"message": "Bid amount must be a whole number or have at most one decimal place"}), 400
        except InvalidOperation:
            return jsonify({"message": "Invalid bid amount format"}), 400

        # GET CREATOR WALLET OR CREATE ONE IF IT DOESN'T EXIST
        creator_wallet = Wallet.query.filter_by(user_id=auction.creator_id).first()
        if not creator_wallet:
            try:
                creator_wallet = Wallet(user_id=auction.creator_id)
                db.session.add(creator_wallet)
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                creator_wallet = Wallet.query.filter_by(user_id=auction.creator_id).first()
                if not creator_wallet:
                    return jsonify({"message": "Error accessing creator wallet"}), 500

        # BID CREATION AND WALLET TRANSFERS
        try:
            wallet.balance -= amount
            creator_amount = amount
            pool_amount = 0
            
            if auction.item_value is not None and auction.item_value > 0:
                total_bid = db.session.query(func.sum(Bid.amount)).filter(Bid.auction_id == auction_id).scalar() or 0
                
                # TRESHOLD CHECK
                if total_bid >= auction.item_value:
                    creator_amount = amount * 0.5
                    pool_amount = amount * 0.5
                    auction.pool_prize += pool_amount
            
            creator_wallet.balance += creator_amount
            
            new_bid = Bid(
                user_id=user_id,
                auction_id=auction_id,
                amount=float(amount_decimal),
                created_at=datetime.now(timezone.utc)
            )
            
            db.session.add(new_bid)
            db.session.commit()

            recalc_bid_uniqueness(auction)
            
            unique_bids = [bid for bid in auction.bids if bid.is_unique]
            is_winner = False
            if unique_bids:
                lowest_unique_bid = min(unique_bids, key=lambda b: b.amount)
                is_winner = (lowest_unique_bid.id == new_bid.id)
            
            logging.info(f"Bid placed successfully. New bidder balance: {wallet.balance}, Creator balance: {creator_wallet.balance}")

            return jsonify({
                "message": "Bid placed successfully",
                "bid_id": new_bid.id,
                "new_balance": wallet.balance,
                "is_winner": is_winner,
                "pool_contribution": pool_amount if pool_amount > 0 else None,
                "current_pool": auction.pool_prize if auction.pool_prize > 0 else None
            }), 201

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error placing bid: {str(e)}")
            return jsonify({"message": "Error placing bid"}), 500

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({"message": "Internal server error"}), 500