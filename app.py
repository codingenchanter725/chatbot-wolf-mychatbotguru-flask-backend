import os
import jwt
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_migrate import Migrate
from sqlalchemy.exc import IntegrityError
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Session, Chat, FAQ
from middleware import token_required
from helper import generate_response_35

app = Flask(__name__)
CORS(app, origins=['*'])
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URL')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
db.init_app(app)
migrate = Migrate(app, db)


@app.route('/')  # ‘https://www.google.com/‘
def home():
    return "Hello, world!"


@app.route('/register', methods=["POST"])
def register():
    if (request.method == 'POST'):
        user_data = request.get_json()
        first_name = user_data.get('first_name')
        last_name = user_data.get('last_name')
        email = user_data.get('email')
        phone = user_data.get('phone')
        password = user_data.get('password')
        session_id = user_data.get('session_id')
        hashed_password = generate_password_hash(password, method='scrypt')

        try:
            new_user = User(
                email=email,
                password=hashed_password,
                first_name=first_name,
                last_name=last_name,
                phone=phone
            )
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            error_info = str(e.orig)
            if 'unique constraint' in error_info:
                return jsonify({'message': 'Email is already taken'}), 400
            else:
                return jsonify({'message': 'An error occurred while creating the user'}), 500

        session = Session.query.filter_by(id=session_id).first()
        if session:
            session.user_id = new_user.id
            db.session.commit()
        return jsonify({
            'message': "User registered Successfully!",
            'user_id': new_user.id
        })
    else:
        return jsonify({'message': 'Bad request'}), 404


@app.route("/admin/login", methods=['POST'])
def admin_login():
    if request.method == 'POST':
        user_data = request.get_json()
        email = user_data.get('email')
        password = user_data.get('password')

        user = User.query.filter_by(email=email, is_admin=True).first()
        if not user or not check_password_hash(user.password, password=password):
            return jsonify({'message': 'Invalid username or password'}), 401

        token = jwt.encode({
            'id': user.id,
            'exp': datetime.utcnow() + timedelta(minutes=30)
        }, app.config['SECRET_KEY'])

        return jsonify({'token': token})
    else:
        return jsonify({'message': 'Bad request'}), 404


@app.route("/chats/<int:session_id>", methods=['GET', 'POST'])
def chat(session_id):
    print(session_id)
    if request.method == 'GET':
        session = Session.query.filter_by(id=session_id).first()
        chat_data = []
        user_data = {}
        if session:
            chats = Chat.query.filter_by(
                session_id=session_id).order_by(Chat.updated_at)
            for chat in chats:
                chat_data.append({
                    'id': chat.id,
                    'text': chat.text,
                    'is_bot': chat.is_bot == 'true',
                    'datetime': chat.updated_at
                })
            if session.user_id:
                user = User.query.filter_by(id=session.user_id).first()
                user_data = {
                    'firstname': user.first_name,
                    'lastname': user.last_name,
                    'email': user.email,
                    'phone': user.phone
                }
            else:
                user_data = {}

        return jsonify({
            'message': 'OK',
            'data': chat_data,
            'user': user_data
        })
    elif request.method == 'POST':
        text = request.json['text']
        session = Session.query.filter_by(id=session_id).first()
        if session:
            chats = Chat.query.filter_by(
                session_id=session_id).order_by(Chat.updated_at.desc())
            chat_data = []
            for chat in chats:
                chat_data.append({
                    "role": "system" if chat.is_bot == 'true' else "user",
                    "content": chat.text
                })
            chat_data.append({
                "role": "user",
                "content": text
            })
            print(chat_data)
            ai_message = generate_response_35(chat_data)

            new_chat_user = Chat(
                session_id=session.id,
                text=text
            )
            db.session.add(new_chat_user)
            db.session.commit()

            new_chat_bot = Chat(
                session_id=session.id,
                text=ai_message,
                is_bot=True
            )
            db.session.add(new_chat_bot)
            db.session.commit()

            return jsonify({
                'message': 'Chat saved successfully',
                'data': {
                    'chat_id': new_chat_user.id,
                    'text_user': text,
                    'text_ai': ai_message
                }
            })
        else:
            new_session = Session()
            db.session.add(new_session)
            db.session.commit()

            chat_data = []
            chat_data.append({
                "role": "user",
                "content": text
            })
            ai_message = generate_response_35(chat_data)

            new_chat_user = Chat(
                session_id=new_session.id,
                text=text
            )
            db.session.add(new_chat_user)
            db.session.commit()

            new_chat_bot = Chat(
                session_id=new_session.id,
                text=ai_message,
                is_bot=True
            )
            db.session.add(new_chat_bot)
            db.session.commit()
            return jsonify({
                'message': 'Session created and chat saved successfully',
                'data': {
                    'session_id': new_session.id,
                    'chat_id': new_chat_user.id,
                    'text_user': text,
                    'text_ai': ai_message
                }
            })
    else:
        return jsonify({'message': 'Bad request'}), 404


@app.route("/faq/<int:faq_id>", methods=['GET', 'POST', 'DELETE'])
def handle_faq(faq_id):
    if request.method == 'GET':
        faqs = FAQ.query.filter_by()
        faq_data = []
        for faq in faqs:
            faq_data.append({
                'id': faq.id,
                'text': faq.text
            })
        return jsonify({
            'message': 'OK',
            'data': faq_data,
        })

    elif request.method == 'POST':
        data = request.json
        text = data['text']

        try:
            faq = FAQ.query.get(faq_id)

            if faq:
                faq.text = text
                db.session.commit()
                return jsonify({
                    'message': 'User updated successfully',
                    'text': text,
                })
            else:
                new_faq = FAQ(
                    text=text,
                )
                db.session.add(new_faq)
                db.session.commit()

                return jsonify({
                    'message': 'User created successfully',
                    'text': text,
                    'faq_id': new_faq.id
                })
        except IntegrityError as e:
            return jsonify({'message': 'An error occurred while creating the user'}), 500

    elif request.method == 'DELETE':
        faq = FAQ.query.get(faq_id)
        if faq:
            db.session.delete(faq)
            db.session.commit()
            return jsonify({'message': 'User deleted successfully'})
        else:
            return jsonify({'message': 'FAQ doesn\'t exact'}), 400


@app.route('/users/<int:user_id>', methods=['GET', 'POST', 'DELETE'])
def handle_user(user_id):
    if request.method == 'GET':
        user = User.query.get(user_id)
        user_data = {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone': user.phone,
        }
        return jsonify({'user': user_data})

    elif request.method == 'POST':
        user_data = request.get_json()
        first_name = user_data.get('first_name')
        last_name = user_data.get('last_name')
        email = user_data.get('email')
        phone = user_data.get('phone')
        password = generate_password_hash(
            user_data.get['password'], method='sha256')

        try:
            user = User.query.get(user_id)

            if user:
                user.phone = phone
                user.email = email
                user.first_name = first_name
                user.last_name = last_name
                user.password = password

                db.session.commit()

                user_data = {
                    'id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'phone': user.phone,
                    'password': user.password,
                }
                return jsonify({
                    'message': 'User updated successfully',
                    'user': user_data
                })
            else:
                new_user = User(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,
                    password=password,
                )
                db.session.add(new_user)
                db.session.commit()

                user_data = {
                    'id': new_user.id,
                    'first_name': new_user.first_name,
                    'last_name': new_user.last_name,
                    'email': new_user.email,
                    'phone': new_user.phone,
                }
                return jsonify({
                    'message': 'User created successfully',
                    'user': user_data
                })
        except IntegrityError as e:
            db.session.rollback()
            error_info = str(e.orig)
            if 'unique constraint' in error_info:
                return jsonify({'message': 'Email is already taken'}), 400
            else:
                return jsonify({'message': 'An error occurred while creating the user'}), 500

    elif request.method == 'DELETE':
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted successfully'})


@app.route("/admin", methods=['POST'])
@token_required
def get_admin_info(current_user):
    data = request.json
    print(current_user)
    admin = User.query.filter_by(is_admin=True).first()
    admin_data = {
        'id': admin.id,
        'email': admin.email,
        'first_name': admin.first_name,
        'last_name': admin.last_name,
        'phone': admin.phone
    }
    return jsonify({
        'message': 'Getting Successfully',
        'data': admin_data
    })


if __name__ == "__main__":
    app.run(port=8000)
