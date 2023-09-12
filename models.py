from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
import datetime

db = SQLAlchemy()


class BaseModel(db.Model):
    __abstract__ = True
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


@event.listens_for(BaseModel, 'before_insert')
def set_created_at(mapper, connection, target):
    target.created_at = datetime.datetime.utcnow()


@event.listens_for(BaseModel, 'before_update')
def set_updated_at(mapper, connection, target):
    target.updated_at = datetime.datetime.utcnow()


class User(BaseModel):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    phone = db.Column(db.String(200), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    password = db.Column(db.String(200), nullable=True)

    session = db.relationship('Session', backref='user', uselist=False)

    def __repr__(self):
        return f"User('{self.first_name} {self.last_name}', '{self.email}')"


class Session(BaseModel):
    __tablename__ = "sessions"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    chats = db.relationship('Chat', backref='session', lazy=True)

    def __repr__(self):
        return f"Session('{self.user_id}')"


class Chat(BaseModel):
    __tablename__ = "chats"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    text = db.Column(db.String, nullable=True, default="")
    is_bot = db.Column(db.String, default=False)  # AI chat
    # include for the prompt but shouldn't show for the user
    is_show = db.Column(db.String, default=True)
    # should show for the user but not include for the prompt
    is_include = db.Column(db.String, default=True)

    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'))
    file_id = db.Column(db.Integer, db.ForeignKey(
        'files.id'), nullable=True)

    def __repr__(self):
        return f"User('{self.text}')"


class FAQ(BaseModel):
    __tablename__ = "faqs"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    text = db.Column(db.String, nullable=True, default="")

    def __repr__(self):
        return f"User('{self.text}')"


class File(BaseModel):
    __tablename__ = "files"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    origin_name = db.Column(db.String(50), nullable=True, default="")
    type = db.Column(db.String, nullable=True, default="")
    size = db.Column(db.Integer, nullable=True, default=0)
    path = db.Column(db.String, nullable=True, default="")
    text = db.Column(db.String, nullable=True, default="")
