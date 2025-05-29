from app import db
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from transformers import pipeline
import os
import secrets
from . import utils 
from .utils import preprocess_text, store_vectors
from .models import Bot, User
from flask import Blueprint, render_template, request, redirect, url_for,  session, jsonify
from . import db, utils


main_bp = Blueprint('main', __name__)
qa_pipeline = pipeline("text-generation", model="gpt2")

# ===================== HOME =====================
@main_bp.route('/')
def index():
    return render_template('index.html')

# ===================== AUTH ROUTES =====================
@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            print('Email already exists!')
            return redirect(url_for('main.register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        print('Registered successfully! Please login.')
        return redirect(url_for('main.login'))

    return render_template('register.html')

# @main_bp.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         email = request.form.get('email')
#         password = request.form.get('password')
#         print(f"Login attempt with email: {email}, password: {password}")

#     if not email or not password:
#         flash('Email and password are required!')
#         return redirect(url_for('main.login'))

#     user = User.query.filter_by(email=email).first()

#     if not user:
#         flash("No account found with that email. Please register first.")
#         return redirect(url_for('main.register'))

#     if not check_password_hash(user.password, password):
#         flash('Incorrect password, please try again.')
#         return redirect(url_for('main.login'))

#         session['user_id'] = user.id
#         session['username'] = user.username
#         flash('Logged in successfully!')
#         return redirect(url_for('main.dashboard'))

#     return render_template('login.html')


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        print(f"Login attempt with email: {email}, password: {password}")

        if not email or not password:
            print('Email and password are required!')
            return redirect(url_for('main.login'))

        user = User.query.filter_by(email=email).first()
        print(f"Found user eith first rank: {user}")

        if not user:
            print("No account found with that email. Please register first.")
            return redirect(url_for('main.register'))

        if not check_password_hash(user.password, password):
            print('Incorrect password, please try again.')
            return redirect(url_for('main.login'))

        # If all good — login user
        session['user_id'] = user.id
        session['username'] = user.username
        print('Logged in successfully!')
        return redirect(url_for('main.dashboard'))

    # For GET request — render login page
    return render_template('login.html')


@main_bp.route('/logout')
def logout():
    session.clear()
    print('Logged out successfully.')
    return redirect(url_for('main.login'))


@main_bp.route('/dashboard')
def dashboard():
    # print("Session data:", session)

    if 'username' not in session:
        print("Please log in first.")
        return redirect(url_for('main.login'))
    user_bots = Bot.query.filter_by(owner=session['username']).all()
    url = user_bots[0].url if user_bots else None
    api_key = user_bots[0].apikey if user_bots else None

    print("User bots:", user_bots)
    return render_template('dashboard.html',
    bots=user_bots,
    user_id=session['user_id'],
    username=session['username'],
    url=url,
    api_key=api_key
    )


@main_bp.route('/create_bot', methods=['POST', 'GET'])
def create_bot():
    if request.method == 'POST':
        bot_name = request.form.get('bot_name')
        company_url = request.form.get('url')

    # created_by = session.get('user_id')  # or however your session stores it
    # if not created_by:
    #     print("You must be logged in to create a bot.")
    #     return redirect(url_for('login'))
    
    if 'user_id' not in session:
        print('Session expired. Please log in again.')
        return redirect(url_for('login'))


    if not bot_name or not company_url:
        print('Bot name and URL are required!')
        return redirect(url_for('main.dashboard'))
    existing_bot = Bot.query.filter_by(name=bot_name, owner=session['username']).first()
    if existing_bot:
        print('A bot with this name already exists!')
        return redirect(url_for('main.dashboard'))

    try:
        print(f"Scraping content from URL: {company_url}")
        content = utils.scrape_website(company_url,bot_name)
        if not content:
            print("No content scraped.")
            print("Failed to scrape content from the provided URL.")
            return redirect(url_for('main.dashboard'))
        # print("Scraped content ", content)
        print(f"Type of content: {type(content)}")

        all_text = " ".join([item['text'] for item in content])

        clean_text = utils.preprocess_text(all_text)
        print(f"Cleaned text preview: {clean_text[:100]}...")

        # Ensure vectors directory exists
        # if not os.path.exists('vectors'):
        # os.makedirs('vectors')

        vector_index_path = f'vectors/{bot_name}_index'
        text_chunks_path = f'vectors/{bot_name}_chunks.pkl'

        utils.store_vectors(clean_text, bot_name)


        api_key = secrets.token_hex(16)
        print(f"Generated API key: {api_key}")

        # Save bot to DB
        new_bot = Bot(
        name=bot_name,
        owner=session['username'],
        url=company_url,
        vector_path=vector_index_path,
        apikey=api_key
        )
        db.session.add(new_bot)
        db.session.commit()

        print(f"Bot created with ID: {new_bot.id}")

        print(f"Bot '{bot_name}' created successfully! Your API key is {api_key}")

    except Exception as e:
        print(f"Error creating bot: {e}")
       

        return redirect(url_for('main.dashboard'))
    # return render_template('chat.html', api_key=new_bot.apikey) It will give most recent bot api_key

    return redirect(url_for('main.dashboard'))




# from flask import Blueprint, request, redirect, url_for, flash, render_template, session, current_app
# from threading import Thread
# from .utils import scrape_and_create_bot
# @main_bp.route('/create_bot', methods=['POST', 'GET'])
# def create_bot():
#     if request.method == 'POST':
#         bot_name = request.form.get('bot_name')
#         company_url = request.form.get('url')

#     if 'username' not in session:
#         print("Please log in first.")
#         return redirect(url_for('main.login'))

#     if not bot_name or not company_url:
#         print('Bot name and URL are required!')
#         return redirect(url_for('main.dashboard'))

#     existing_bot = Bot.query.filter_by(name=bot_name, owner=session['username']).first()
#     if existing_bot:
#         print('A bot with this name already exists!')
#         return redirect(url_for('main.dashboard'))

#     try:
#         api_key = secrets.token_hex(16)
#         print(f"Generated API key: {api_key}")

#         from threading import Thread
#         from .utils import scrape_and_create_bot
#         # Start background thread
#         app = current_app._get_current_object()
#         thread = Thread(target=scrape_and_create_bot, args=(company_url, bot_name, session['username'], api_key,app))
#         thread.daemon = True  # Ensure thread exits when main program does
#         thread.start()

#         flash(f"Bot '{bot_name}' creation started! (Scraping in background, API key: {api_key})")

#     except Exception as e:
#         print(f"Error creating bot: {e}")
#         flash("Failed to create bot. Please check the URL or try again.")

#     return redirect(url_for('main.dashboard'))

@main_bp.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.json
    print("Received chat API request:", data)
    # api_key = request.headers.get('X-API-Key')
    api_key = data.get('api_key')

    if not api_key or not data or 'query' not in data:
        return jsonify({'error': 'API key and query are required.'}), 400
    
    try:
        # bot = Bot.query.filter_by(apikey=data['api_key']).first()
        bot = Bot.query.filter_by(apikey=api_key).first()
        if not bot:
            return jsonify({'error': 'Invalid API key.'}), 401
        print(f"Found bot: {bot.name}, answering query...")

        response = utils.answer_query(bot.name, data['query'])
        return jsonify({'response': response})

    except Exception as e:
        print(f"Error handling chat API request: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# One-time ask API endpoint
@main_bp.route('/api/ask', methods=['POST'])
def ask_api():
    data = request.json
    print("Received ask API request:", data)

    if not data or 'url' not in data or 'query' not in data:
        return jsonify({'error': 'URL and query are required.'}), 400

    try:
        answer = utils.process_url_and_answer_query(data['url'], data['query'])
        return jsonify({'answer': answer})

    except Exception as e:
        print(f"Error processing ask API request: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@main_bp.route('/delete_bots', methods=['POST'])
def delete_bots():
    bot_ids = request.form.getlist('bot_ids')

    if not bot_ids:
        flash('No bots selected for deletion.', 'warning')
        return redirect(url_for('main.dashboard'))

    bots_to_delete = Bot.query.filter(Bot.id.in_(bot_ids)).all()

    for bot in bots_to_delete:
        db.session.delete(bot)

    db.session.commit()
    flash(f'Successfully deleted {len(bots_to_delete)} bot(s).', 'success')
    return redirect(url_for('main.dashboard'))
