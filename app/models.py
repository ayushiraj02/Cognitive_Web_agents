from . import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"

class Bot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    owner = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(300), nullable=False)
    apikey = db.Column(db.String(50), nullable=False)
    vector_path = db.Column(db.String(300))  
    # created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


    def __repr__(self):
        return f"<Bot {self.name} owned by {self.owner}>"
