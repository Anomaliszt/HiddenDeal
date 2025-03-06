from datetime import datetime, timezone

from extensions import db


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bids = db.relationship('Bid', backref='user', lazy=True)
    wallet = db.relationship('Wallet', backref='user', uselist=False, lazy=True)


class Auction(db.Model):
    __tablename__ = 'auction'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    starting_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)
    winner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_value = db.Column(db.Float, nullable=True)
    pool_prize = db.Column(db.Float, default=0.0)
    pool_distributed = db.Column(db.Boolean, default=False)
    bids = db.relationship('Bid', backref='auction', lazy=True)
    creator = db.relationship('User', foreign_keys=[creator_id], backref='created_auctions')
    pool_winners = db.relationship('PoolPrizeWinner', backref='auction', lazy=True)

    def __init__(self, **kwargs):
        super(Auction, self).__init__(**kwargs)
        if self.expires_at and self.expires_at.tzinfo is None:
            self.expires_at = self.expires_at.replace(tzinfo=timezone.utc)


class Bid(db.Model):
    __tablename__ = 'bid'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    auction_id = db.Column(db.Integer, db.ForeignKey('auction.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    is_unique = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        super(Bid, self).__init__(**kwargs)
        if self.created_at and self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)


class Wallet(db.Model):
    __tablename__ = 'wallet'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    balance = db.Column(db.Float, default=1000.0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        super(Wallet, self).__init__(**kwargs)


class PoolPrizeWinner(db.Model):
    __tablename__ = 'pool_prize_winner'
    id = db.Column(db.Integer, primary_key=True)
    auction_id = db.Column(db.Integer, db.ForeignKey('auction.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rank = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = db.relationship('User', backref='pool_prizes')