"""
Auctions API Blueprint - Handles all auction-related endpoints

This module provides the following endpoints:
- GET /api/auctions/ - List all auctions
- GET /api/auctions/<id> - Get details for a specific auction
- POST /api/auctions/ - Create a new auction
- GET /api/auctions/<id>/bids - Get all bids for an auction
- GET /api/auctions/<id>/pool - Get pool prize information for an auction
"""
from flask import Blueprint, request, jsonify
from extensions import db
from models import Auction, Bid, User, PoolPrizeWinner, Wallet
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from sqlalchemy import func
from routes.winners import recalc_bid_uniqueness

auctions_bp = Blueprint('auctions', __name__)

@auctions_bp.route('/', methods=['GET'])
def get_auctions():
    """
    Get all auctions
    Returns:
        List of all auctions with their details
    """
    auctions = Auction.query.all()
    current_time = datetime.now(timezone.utc)
    
    result = []
    for auction in auctions:
        # TIMEZONE VERIFICATION
        expires_at = auction.expires_at.replace(tzinfo=timezone.utc) if auction.expires_at.tzinfo is None else auction.expires_at
        
        # STATUS UPDATE
        if current_time > expires_at and auction.status != 'expired':
            auction.status = 'expired'
            db.session.add(auction)
        
        creator = User.query.get(auction.creator_id)
        creator_username = creator.username if creator else f"User #{auction.creator_id}"
        result.append({
            "id": auction.id,
            "title": auction.title,
            "description": auction.description,
            "starting_price": auction.starting_price,
            "status": auction.status,
            "created_at": auction.created_at.isoformat(),
            "expires_at": auction.expires_at.isoformat(),
            "winner_id": auction.winner_id,
            "creator_id": auction.creator_id,
            "creator_username": creator_username,
            "item_value": auction.item_value
        })
    
    # IF AUCTION EXPIRED, COMMIT CHANGES
    if any(auction.status == 'expired' for auction in auctions):
        db.session.commit()
    
    return jsonify(result), 200

@auctions_bp.route('/<int:auction_id>', methods=['GET'])
@jwt_required()
def get_auction(auction_id):
    """
    Get details for a specific auction
    Returns:
        Auction details including user's bids and winning bid info
    """
    current_user_id = get_jwt_identity()
    auction = Auction.query.get_or_404(auction_id)
    current_time = datetime.now(timezone.utc)
    expires_at = auction.expires_at.replace(tzinfo=timezone.utc) if auction.expires_at.tzinfo is None else auction.expires_at

    # STATUS UPDATE
    if current_time > expires_at and auction.status != 'expired':
        auction.status = 'expired'
        db.session.commit()

    # FIND LOWEST UNIQUE BIDDER AMONGST USERS
    recalc_bid_uniqueness(auction)

    lowest_unique_bid_info = None
    unique_bids = [bid for bid in auction.bids if bid.is_unique]
    if unique_bids:
        lowest_unique_bid = min(unique_bids, key=lambda b: b.amount)
        winner_user = User.query.get(lowest_unique_bid.user_id)
        lowest_unique_bid_info = {
            "bid_id": lowest_unique_bid.id,
            "user_id": lowest_unique_bid.user_id,
            "username": winner_user.username,
            "is_users_bid": lowest_unique_bid.user_id == int(current_user_id)
        }

    # FILTER ONLY USER'S BIDS
    bids = []
    for bid in auction.bids:
        if bid.user_id == int(current_user_id):
            is_winner = lowest_unique_bid_info and bid.id == lowest_unique_bid_info["bid_id"]
            bids.append({
                "id": bid.id,
                "user_id": bid.user_id,
                "amount": bid.amount,
                "is_unique": bid.is_unique,
                "is_winner": is_winner,
                "created_at": bid.created_at.isoformat()
            })
            
    result = {
        "id": auction.id,
        "title": auction.title,
        "description": auction.description,
        "starting_price": auction.starting_price,
        "status": auction.status,
        "created_at": auction.created_at.isoformat(),
        "expires_at": auction.expires_at.isoformat(),
        "winner_id": auction.winner_id,
        "creator_id": auction.creator_id,
        "bids": bids,
        "lowest_unique_bid": lowest_unique_bid_info
    }
    return jsonify(result), 200

@auctions_bp.route('/<int:auction_id>/bids', methods=['GET'])
@jwt_required()
def get_auction_bids(auction_id):
    """
    Get all bids for a specific auction
    Returns:
        List of all bids for the auction
    """
    auction = Auction.query.get_or_404(auction_id)
    all_bids = [{
        "amount": bid.amount,
        "created_at": bid.created_at.isoformat(),
        "user_id": bid.user_id,
        "username": User.query.get(bid.user_id).username if User.query.get(bid.user_id) else f"User #{bid.user_id}"
    } for bid in auction.bids]
    return jsonify(all_bids), 200

@auctions_bp.route('/', methods=['POST'])
@jwt_required()
def create_auction():
    """
    Create a new auction
    Returns:
        Created auction ID and confirmation message
    """
    data = request.get_json()
    if not data or not all(k in data for k in ('title', 'starting_price', 'expires_at')):
        return jsonify({"message": "Missing required fields"}), 400
    try:
        expires_at = datetime.fromisoformat(data['expires_at'])
    except ValueError:
        return jsonify({"message": "Invalid date format for expires_at"}), 400

    user_id = get_jwt_identity()
    
    item_value = data.get('item_value')
    if item_value is not None:
        try:
            item_value = float(item_value)
            if item_value <= 0:
                return jsonify({"message": "Item value must be positive"}), 400
        except ValueError:
            return jsonify({"message": "Invalid item value"}), 400

    new_auction = Auction(
        title=data['title'],
        description=data.get('description', ''),
        starting_price=data['starting_price'],
        expires_at=expires_at,
        status='active',
        creator_id=user_id,
        item_value=item_value
    )
    db.session.add(new_auction)
    db.session.commit()
    return jsonify({"id": new_auction.id, "message": "Auction created"}), 201

@auctions_bp.route('/<int:auction_id>/pool', methods=['GET'])
@jwt_required()
def get_pool_info(auction_id):
    """
    Get pool prize information for an auction   
    Returns:
        Pool prize information including top bidders and winners
    """
    auction = Auction.query.get_or_404(auction_id)
    
    top_bidders_query = db.session.query(
        Bid.user_id,
        func.count(Bid.id).label('bid_count'),
        User.username
    ).join(User).filter(
        Bid.auction_id == auction_id
    ).group_by(
        Bid.user_id, User.username
    ).order_by(
        func.count(Bid.id).desc()
    ).limit(3).all()
    
    top_bidders = []
    
    for i, (user_id, bid_count, username) in enumerate(top_bidders_query):
        potential_percentage = 0
        if i == 0:
            potential_percentage = 60
        elif i == 1:
            potential_percentage = 30
        elif i == 2:
            potential_percentage = 10
            
        potential_amount = (auction.pool_prize * potential_percentage / 100) if auction.pool_prize else 0
        
        top_bidders.append({
            "user_id": user_id,
            "username": username,
            "bid_count": bid_count,
            "rank": i + 1,
            "potential_percentage": potential_percentage,
            "potential_amount": potential_amount
        })
    
    winners = []
    if auction.pool_distributed:
        pool_winners = PoolPrizeWinner.query.filter_by(auction_id=auction_id).order_by(PoolPrizeWinner.rank).all()
        winners = [{
            "user_id": winner.user_id,
            "username": User.query.get(winner.user_id).username,
            "rank": winner.rank,
            "percentage": winner.percentage,
            "amount": winner.amount
        } for winner in pool_winners]
    
    return jsonify({
        "auction_id": auction.id,
        "item_value": auction.item_value,
        "pool_prize": auction.pool_prize,
        "pool_distributed": auction.pool_distributed,
        "top_bidders": top_bidders,
        "winners": winners if auction.pool_distributed else []
    }), 200