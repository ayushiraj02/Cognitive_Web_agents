from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///webbot.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your-secret-key'

    
    db.init_app(app)

    from .routes import main_bp
    app.register_blueprint(main_bp)

    

    
    with app.app_context():
        from . import models  # Import models to ensure they are registered with SQLAlchemy
        # db.drop_all()        #TO delete all tables
        db.create_all()       

    return app

