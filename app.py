import os
from io import StringIO
import jwt
import csv
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, make_response, Response
from flask_migrate import Migrate
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Session, Chat, FAQ, File
from middleware import token_required
from helper import generate_response_35, convert_file_to_text
from utils import generate_unique_filename, get_short_type_from_real_type, optimize_string

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

        session = Session.query.filter_by(user_id=user.id).first()
        session_id = ""
        if session:
            session_id = session.id
        else:
            admin_session = Session(
                user_id=user.id
            )
            db.session.add(admin_session)
            db.session.commit()
            session_id = admin_session.id

        return jsonify({
            'token': token,
            'session_id': session_id
        })
    else:
        return jsonify({'message': 'Bad request'}), 404


@app.route("/chats/<int:session_id>", methods=['GET', 'POST', 'DELETE'])
def chat(session_id):
    chat_data = []
    is_admin = request.args.get('is_admin')
    if request.method == 'GET':
        session = Session.query.filter_by(id=session_id).first()
        if is_admin:
            session = Session.query.filter_by(is_admin=True).first()
            if not session:
                session = Session(
                    is_admin=True
                )
                db.session.add(session)
                db.session.commit()
        chat_data = []
        user_data = {}
        if session:
            chats = Chat.query.filter_by(
                session_id=session_id).order_by(Chat.updated_at)
            for chat in chats:
                chat_detail = {
                    'id': chat.id,
                    'text': chat.text,
                    'is_bot': chat.is_bot == True,
                    'datetime': chat.updated_at,
                }
                if chat.file_id:
                    file = File.query.filter_by(id=chat.file_id).first()
                    file_data = {
                        'id': file.id,
                        'name': file.origin_name,
                        'size': file.size,
                        'text': file.text
                    }
                    chat_detail['file'] = file_data

                chat_data.append(chat_detail)
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
                'user': user_data, 
                'session_id': session.id
            })
        return jsonify({
            'message': 'OK',
            'data': [],
            'user': {}, 
            'session_id': 0
        })
    elif request.method == 'POST':
        session = Session.query.filter_by(id=session_id).first()
        chat_data = get_admin_prompt()
        new_session = None

        if session:
            if not is_admin:
                chats = Chat.query.filter_by(
                    session_id=session_id).order_by(Chat.updated_at.desc())
                for chat in chats:
                    if chat.is_include == False:
                        continue
                    chat_data.append({
                        "role": "system" if chat.is_bot == True else "user",
                        "content": chat.text
                    })
                    if chat.file_id:
                        file = File.query.filter_by(id=chat.file_id).first()
                        file_content = "" + file.text
                        content_array = optimize_string(file_content, 500)
                        for content in content_array:
                            chat_data.append({
                                "role": "user",
                                "content": content
                            })
        else:
            new_session = Session()
            db.session.add(new_session)
            db.session.commit()
            session = new_session
            print('new_session_id', session.id)
        print('new_session_id1', session.id)

        if request.is_json:
            text = request.json['text']
            chat_data.append({
                "role": "user",
                "content": text
            })
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
                'message': 'Chat saved successfully' if not new_session else 'Session created and chat saved successfully',
                'data': {
                    'session_id': new_session.id if new_session else None,
                    'chat_id': new_chat_user.id,
                    'bot_chat_id': new_chat_bot.id,
                    'text_user': text,
                    'text_ai': ai_message
                }
            })
        else:
            file = request.files['file']
            if file.filename == '':
                return 'No file selected', 400
            text = request.form.get('text')

            upload_folder = 'uploads/'
            os.makedirs(upload_folder, exist_ok=True)

            origin_name = file.filename
            file_data = file.read()
            file_type = file.content_type
            file_size = len(file_data)
            file_path = upload_folder + generate_unique_filename() + '_' + file.filename

            try:
                with open(file_path, 'wb') as f:
                    f.write(file_data)
            except Exception as e:
                return f'Error saving the file: {str(e)}', 500

            file_content = convert_file_to_text(
                file_path, get_short_type_from_real_type(file_type))

            new_file = File(
                origin_name=origin_name,
                size=file_size,
                type=file_type,
                path='/'+file_path,
                text=file_content
            )
            db.session.add(new_file)
            db.session.commit()

            content_text = "" + text + "\n" + file_content

            content_array = optimize_string(content_text, 500) # 8192
            for content in content_array:
                print(len(content), "\n")
                chat_data.append({
                    "role": "user",
                    "content": content
                })

            ai_message = generate_response_35(chat_data)

            new_chat_user = Chat(
                session_id=session.id,
                text=text,
                file_id=new_file.id
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
                'message': 'Chat saved successfully' if not new_session else 'Session created and chat saved successfully',
                'data': {
                    'session_id': new_session.id if new_session else None,
                    'chat_id': new_chat_user.id,
                    'bot_chat_id': new_chat_bot.id,
                    'text_user': text,
                    'text_ai': ai_message
                }
            })
    elif request.method == "DELETE":
        chat_id = session_id
        chat = Chat.query.filter_by(id=chat_id).first()
        if chat:
            db.session.delete(chat)
            db.session.commit()
            return jsonify({
                'message': 'Deleted successfully', 
                'chat_id': chat_id,
            })
        else:
            return jsonify({
                'message': 'Chat_id doesn\'t exist', 
                'chat_id': chat_id
            })

    else:
        return jsonify({'message': 'Bad request'}), 404


@app.route("/admin/initial_prompt", methods=['GET', 'PUT'])
def handle_initial_prompt():
    if request.method == "GET":
        initial_prompt_chat = Chat.query.filter_by(is_initial_prompt=True).first()
        initial_prompt = ""
        if initial_prompt_chat:
            initial_prompt = initial_prompt_chat.text
            db.session.commit()
        else:
            new_session_for_initial_prompt = Session()
            db.session.add(new_session_for_initial_prompt)
            db.session.commit()

            initial_prompt_chat = Chat(
                session_id=new_session_for_initial_prompt.id,
                text="",
                is_initial_prompt=True
            )
            db.session.add(initial_prompt_chat)
            db.session.commit()
        return jsonify({
            'message': 'OK',
            'data': {
                'text': initial_prompt,
            }
        })
    elif request.method == 'PUT':
        text = request.json['text']
        initial_prompt_chat = Chat.query.filter_by(is_initial_prompt='True').first()
        initial_prompt_chat.text = text
        db.session.commit()
        return jsonify({
            'message': 'OK',
            'data': {
                'text': text,
            }
        })
    else:
        return jsonify({'message': 'Bad request'}), 404

def get_admin_prompt():
    admin_session = Session.query.filter_by(is_admin=True).first()
    prompt_chat = Chat.query.filter_by(is_initial_prompt=True).first()
    initial_prompt = prompt_chat.text
    chat_data = [
        {
            "role": 'user', 
            'content': initial_prompt
        }
    ]
    if admin_session:
        admin_chats = Chat.query.filter_by(session_id=admin_session.id)
        if admin_chats:
            for chat in admin_chats:
                if chat.is_include == False:
                    continue
                chat_data.append({
                    "role": "system" if chat.is_bot == True else "user",
                    "content": chat.text
                })
                if chat.file_id:
                    file = File.query.filter_by(id=chat.file_id).first()
                    file_content = "" + file.text
                    content_array = optimize_string(file_content, 500)
                    for content in content_array:
                        chat_data.append({
                            "role": "user",
                            "content": content
                        })
    return chat_data

if __name__ == "__main__":
    app.run(port=8000)
