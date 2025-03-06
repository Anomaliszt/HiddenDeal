from flask import Flask
from config import Config
from extensions import db, bcrypt, jwt
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    
    from routes.auth import auth_bp
    from routes.auctions import auctions_bp
    from routes.bids import bids_bp
    from routes.winners import winners_bp
    from routes.wallet import wallet_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(auctions_bp, url_prefix='/api/auctions')
    app.register_blueprint(bids_bp, url_prefix='/api/bids')
    app.register_blueprint(winners_bp, url_prefix='/api/winners')
    app.register_blueprint(wallet_bp, url_prefix='/api/wallet')
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
