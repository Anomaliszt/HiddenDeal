"""
Authentication API Blueprint - Handles user registration and login

This module provides the following endpoints:
- POST /api/auth/register - Register new users with automatic wallet creation
- POST /api/auth/login - Authenticate users and issue JWT tokens
"""
from flask import Blueprint, request, jsonify
from extensions import db, bcrypt
from models import User, Wallet
from flask_jwt_extended import create_access_token

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user
    Returns:
        Registration confirmation message
    """
    data = request.get_json()
    
    if not data or not all(k in data for k in ('username', 'email', 'password')):
        return jsonify({"message": "Missing required fields"}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"message": "Username already exists"}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"message": "Email already exists"}), 400
    
    try:
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        new_user = User(
            username=data['username'],
            email=data['email'],
            password_hash=hashed_password
        )
        db.session.add(new_user)
        db.session.flush()
        
        # CHECK IF WALLET EXISTS, IF NOT CREATE ONE
        existing_wallet = Wallet.query.filter_by(user_id=new_user.id).first()
        if not existing_wallet:
            wallet = Wallet(user_id=new_user.id)
            db.session.add(wallet)
        
        db.session.commit()
        return jsonify({"message": "User registered successfully"}), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error during registration: {str(e)}")
        return jsonify({"message": f"Error during registration: {str(e)}"}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate a user and issue JWT token
    Returns:
        JWT token for authenticated requests
    """
    data = request.get_json()
    if not data or not all(k in data for k in ('email', 'password')):
        return jsonify({"message": "Missing required fields"}), 400

    user = User.query.filter_by(email=data['email']).first()
    if user and bcrypt.check_password_hash(user.password_hash, data['password']):
        access_token = create_access_token(identity=str(user.id))
        return jsonify({"token": access_token}), 200
    return jsonify({"message": "Invalid credentials"}), 401