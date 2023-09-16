import os
import jwt
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, make_response
from flask_migrate import Migrate
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Session, Chat, FAQ, File
from middleware import token_required
from helper import generate_response_4, convert_file_to_text
from utils import generate_unique_filename, getS_short_type_from_real_type, split_string

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


@app.route("/chats/<int:session_id>", methods=['GET', 'POST'])
def chat(session_id):
    if request.method == 'GET':
        session = Session.query.filter_by(id=session_id).first()
        chat_data = []
        user_data = {}
        if session:
            chats = Chat.query.filter_by(
                session_id=session_id).order_by(Chat.updated_at)
            for chat in chats:
                chat_detail = {
                    'id': chat.id,
                    'text': chat.text,
                    'is_bot': chat.is_bot == 'true',
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
            'user': user_data
        })
    elif request.method == 'POST':
        if request.is_json:
            text = request.json['text']
            session = Session.query.filter_by(id=session_id).first()
            chat_data = get_admin_prompt()
            if session:
                chats = Chat.query.filter_by(
                    session_id=session_id).order_by(Chat.updated_at.desc())
                for chat in chats:
                    if chat.is_include == False:
                        continue
                    chat_data.append({
                        "role": "system" if chat.is_bot == 'true' else "user",
                        "content": chat.text
                    })
                chat_data.append({
                    "role": "user",
                    "content": text
                })
                ai_message = generate_response_4(chat_data)

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
                        'bot_chat_id': new_chat_bot.id,
                        'text_user': text,
                        'text_ai': ai_message
                    }
                })
            else:
                new_session = Session()
                db.session.add(new_session)
                db.session.commit()

                chat_data.append({
                    "role": "user",
                    "content": text
                })
                ai_message = generate_response_4(chat_data)

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
                file_path, getS_short_type_from_real_type(file_type))

            new_file = File(
                origin_name=origin_name,
                size=file_size,
                type=file_type,
                path='/'+file_path,
                text=file_content
            )
            db.session.add(new_file)
            db.session.commit()

            content_text = "This is the details for https://www.afrilabs.com and https://afrilabsgathering.com\n, learn the detail from above description\n" + text + "\n" + file_content

            chats = Chat.query.filter_by(
                session_id=session_id).order_by(Chat.updated_at.desc())
            chat_data = []
            for chat in chats:
                if chat.is_include == False:
                    continue
                chat_data.append({
                    "role": "system" if chat.is_bot == 'true' else "user",
                    "content": chat.text
                })

            content_array = split_string(content_text, 12000)
            for content in content_array:
                chat_data.append({
                    "role": "user",
                    "content": content
                })

            ai_message = generate_response_4(chat_data)

            new_chat_user = Chat(
                session_id=session_id,
                text=text,
                file_id=new_file.id
            )
            db.session.add(new_chat_user)
            db.session.commit()

            new_chat_bot = Chat(
                session_id=session_id,
                text=ai_message,
                is_bot=True
            )
            db.session.add(new_chat_bot)
            db.session.commit()

            return jsonify({
                'message': 'OK',
                'data': {
                    'chat_id': '0',
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
@token_required
def handle_user(current_user, user_id):
    if request.method == 'GET':

        users = User.query.filter_by()
        user_data = []
        for user in users:
            user_data.append({
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone': user.phone,
            })
        return jsonify({
            'message': 'OK',
            'data': user_data,
        })

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


@app.route('/admin', methods=['GET'])
@token_required
def analysis(current_user):
    if request.method == "GET":
        # Replace with your start time
        start_time = datetime(2022, 1, 1, 0, 0, 0)
        # Replace with your end time
        end_time = datetime(2024, 1, 31, 23, 59, 59)
        chat_count = Chat.query.filter(
            Chat.updated_at >= start_time, Chat.updated_at <= end_time).count()
        users = User.query.filter_by()
        user_count = users.count()

        total_chat_count_by_user = 0
        max_chat_count_by_one_user = 0
        max_duration = 0

        for user in users:
            session = Session.query.filter_by(user_id=user.id).first()
            if session:
                chats = Chat.query.filter_by(session_id=session.id).all()
                chat_len = len(chats)
                first_chat: datetime = chats[0].updated_at if chat_len > 0 else 0
                last_chat: datetime = chats[-1].updated_at if chat_len > 0 else 0
                duration = (
                    last_chat - first_chat).total_seconds() if first_chat and last_chat else 0

                total_chat_count_by_user += chat_len

                if max_chat_count_by_one_user < chat_len:
                    max_chat_count_by_one_user = chat_len

                if max_duration < duration:
                    max_duration = duration

        average_chat_count_by_user = total_chat_count_by_user / user_count
        total_download_count = db.session.query(func.sum(Session.download_count)).scalar()

        print(total_download_count)
        return jsonify({
            'message': "OK",
            'data': {
                'chat_count': chat_count,
                'user_count': user_count,
                'average_chat_count_by_user': average_chat_count_by_user,
                'max_duration': max_duration,
                'max_chat_count_by_one_user': max_chat_count_by_one_user,
                'total_download_count': total_download_count,
            }
        })
    else:
        return jsonify({'message': 'Bad request'}), 404


def get_admin_prompt():
    admin_user = User.query.filter_by(is_admin=True).first()
    admin_session = Session.query.filter_by(
        user_id=admin_user.id).first()
    admin_chats = Chat.query.filter_by(session_id=admin_session.id)
    chat_data = []
    for chat in admin_chats:
        if chat.is_include == False:
            continue
        chat_data.append({
            "role": "system" if chat.is_bot == 'true' else "user",
            "content": chat.text
        })
        if chat.file_id:
            file = File.query.filter_by(id=chat.file_id).first()
            file_content = "This is the details for https://www.afrilabs.com and https://afrilabsgathering.com\n, learn the detail from above description\n" + file.text
            content_array = split_string(file_content, 12000)
            for content in content_array:
                chat_data.append({
                    "role": "user",
                    "content": content
                })
    return chat_data


@app.route('/download/transcript/<int:session_id>', methods=['GET'])
def download_transcript_by_user(session_id):
    chats = Chat.query.filter_by(session_id=session_id)
    chat_history = "Chat history\n\n\n"

    for chat in chats:
        if chat.is_show == False:
            continue
        if chat.is_bot:
            chat_history += f'Bot: ${chat.text}\n\n'
        else:
            chat_history += f'User: ${chat.text}\n\n'

    response = make_response(chat_history)
    response.headers['Content-Disposition'] = 'attachment; filename=transcript.txt'
    response.headers['Content-Type'] = 'text/plain'
    return response

if __name__ == "__main__":
    app.run(port=8000)
