from app import create_app
from extensions import db
from models import User


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Database created successfully.")
        db.session.commit()
