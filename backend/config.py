class Config:
    SECRET_KEY = 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///reverse_auction.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = 'your-jwt-secret-key'
