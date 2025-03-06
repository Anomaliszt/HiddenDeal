"""
Wallet API Blueprint - Handles wallet-related functionality

This module provides the following endpoints:
- GET /api/wallet/ - Get current user's wallet balance
- POST /api/wallet/add/<amount> - Add funds to current user's wallet
- POST /api/wallet/admin/add - Admin endpoint to add funds to any user's wallet
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Wallet
from sqlalchemy.exc import IntegrityError

wallet_bp = Blueprint('wallet', __name__)

@wallet_bp.route('/', methods=['GET'])
@jwt_required()
def get_balance():
    """
    Get current user's wallet balance
    Returns:
        User's wallet balance and last update timestamp
    """
    user_id = get_jwt_identity()
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    
    if not wallet:
        try:
            wallet = Wallet(user_id=user_id)
            db.session.add(wallet)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            wallet = Wallet.query.filter_by(user_id=user_id).first()
            if not wallet:
                return jsonify({"message": "Error creating wallet"}), 500
    
    return jsonify({
        "balance": wallet.balance,
        "updated_at": wallet.updated_at.isoformat()
    }), 200

@wallet_bp.route('/add/<float:amount>', methods=['POST'])
@jwt_required()
def add_funds(amount):
    """
    Add funds to the current user's wallet
    Returns:
        Success message and new balance
    """
    if amount <= 0:
        return jsonify({"message": "Amount must be positive"}), 400
        
    user_id = get_jwt_identity()
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    
    if not wallet:
        wallet = Wallet(user_id=user_id)
        db.session.add(wallet)
    
    wallet.balance += amount
    db.session.commit()
    
    return jsonify({
        "message": f"Added ${amount:.2f} to wallet",
        "new_balance": wallet.balance
    }), 200

@wallet_bp.route('/admin/add', methods=['POST'])
@jwt_required()
def admin_add_funds():
    """
    Admin endpoint to add funds to any user's wallet
    ADMIN is ID 1
    Returns:
        Confirmation message and updated balance information
    """
    current_user_id = int(get_jwt_identity())
    if current_user_id != 1:
        return jsonify({"message": "Unauthorized. Admin access required."}), 403
    
    data = request.get_json()
    if not data or not all(k in data for k in ('user_id', 'amount')):
        return jsonify({"message": "Missing required fields"}), 400
        
    user_id = int(data['user_id'])
    amount = float(data['amount'])
    
    if amount <= 0:
        return jsonify({"message": "Amount must be positive"}), 400
        
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    
    if not wallet:
        wallet = Wallet(user_id=user_id)
        db.session.add(wallet)
    
    old_balance = wallet.balance
    wallet.balance += amount
    db.session.commit()
    
    return jsonify({
        "message": f"Added ${amount:.2f} to user {user_id}'s wallet",
        "user_id": user_id,
        "old_balance": old_balance,
        "new_balance": wallet.balance
    }), 200