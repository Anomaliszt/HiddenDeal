"""
Winners API Blueprint - Handles winner determination and prize distribution

This module provides the following endpoints:
- GET /api/winners/<auction_id> - Get auction winner information
- recalc_bid_uniqueness() - Utility function for determining unique bids
- distribute_pool_prize() - Handles distribution of pool prizes
"""
from flask import Blueprint, jsonify
from extensions import db
from models import Auction, Bid, User, PoolPrizeWinner, Wallet
from flask_jwt_extended import jwt_required
from datetime import datetime, timezone
from collections import Counter
from sqlalchemy import func

winners_bp = Blueprint('winners', __name__)

def recalc_bid_uniqueness(auction):
    """
    Recalculates which bids in the auction are unique.
    """
    bid_amounts = [bid.amount for bid in auction.bids]
    amount_counts = Counter(bid_amounts)
    
    for bid in auction.bids:
        is_unique = amount_counts[bid.amount] == 1
        if bid.is_unique != is_unique:
            bid.is_unique = is_unique
            db.session.add(bid)
    
    db.session.commit()

def distribute_pool_prize(auction_id):
    """
    Distribute the pool prize to the top three bidders
    - 1st place: 60%
    - 2nd place: 30%
    - 3rd place: 10%
    """
    try:
        auction = Auction.query.get(auction_id)
        if not auction or auction.pool_distributed or auction.pool_prize <= 0:
            return False, "Pool prize already distributed or not available"
            
        # GET TOP 3 BIDDERS
        top_bidders = db.session.query(
            Bid.user_id, 
            func.count(Bid.id).label('bid_count')
        ).filter(
            Bid.auction_id == auction_id
        ).group_by(
            Bid.user_id
        ).order_by(
            func.count(Bid.id).desc()
        ).limit(3).all()
        
        if not top_bidders:
            return False, "No bidders found"

        percentages = {1: 60, 2: 30, 3: 10}
        winners = []
        
        # UPDTATE USER BALANCE
        for rank, (user_id, _) in enumerate(top_bidders, 1):
            if rank > 3:
                break
                
            percentage = percentages.get(rank, 0)
            amount = auction.pool_prize * (percentage / 100)
            

            wallet = Wallet.query.filter_by(user_id=user_id).first()
            if wallet:
                wallet.balance += amount
                
            winner = PoolPrizeWinner(
                auction_id=auction_id,
                user_id=user_id,
                rank=rank,
                percentage=percentage,
                amount=amount
            )
            db.session.add(winner)
            winners.append((user_id, percentage, amount))
            
        auction.pool_distributed = True
        db.session.commit()
        
        return True, winners
        
    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"Error distributing pool prize: {str(e)}")
        return False, str(e)

@winners_bp.route('/<int:auction_id>', methods=['GET'])
@jwt_required()
def get_winner(auction_id):
    """
    Get winner information for a completed auction
    Returns:
        Winner details and pool prize distribution information
    """
    auction = Auction.query.get_or_404(auction_id)
    
    # CHECK OR UPDATE AUCTION STATUS
    current_time = datetime.now(timezone.utc)
    expires_at = auction.expires_at.replace(tzinfo=timezone.utc) if auction.expires_at.tzinfo is None else auction.expires_at
    
    if current_time < expires_at:
        return jsonify({"message": "Auction is still active"}), 400
        
    if auction.status != 'expired':
        auction.status = 'expired'
        
    recalc_bid_uniqueness(auction)
    
    unique_bids = [bid for bid in auction.bids if bid.is_unique]
    
    if not unique_bids:
        db.session.commit()
        return jsonify({"message": "No unique bids found"}), 404
        
    lowest_unique_bid = min(unique_bids, key=lambda b: b.amount)
    winner_id = lowest_unique_bid.user_id
    
    if auction.winner_id != winner_id:
        auction.winner_id = winner_id
        
    pool_info = {}
    if not auction.pool_distributed and auction.pool_prize > 0:
        success, result = distribute_pool_prize(auction_id)
        if success:
            pool_winners = PoolPrizeWinner.query.filter_by(auction_id=auction_id).all()
            pool_info = {
                "distributed": True,
                "winners": [{
                    "user_id": winner.user_id,
                    "username": User.query.get(winner.user_id).username,
                    "rank": winner.rank,
                    "percentage": winner.percentage,
                    "amount": winner.amount
                } for winner in pool_winners]
            }
        else:
            pool_info = {
                "distributed": False,
                "message": result
            }
            
    db.session.commit()
    
    winner = User.query.get_or_404(winner_id)
    
    return jsonify({
        "auction_id": auction_id,
        "winner_id": winner_id,
        "winner_username": winner.username,
        "winning_bid_amount": lowest_unique_bid.amount,
        "winning_bid_created_at": lowest_unique_bid.created_at.isoformat(),
        "pool_prize": auction.pool_prize,
        "pool_prize_info": pool_info
    }), 200