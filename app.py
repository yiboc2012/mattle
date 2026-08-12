from flask import Flask, render_template, request, jsonify
import random
import sqlite3
import time
from collections import defaultdict

app = Flask(__name__)
DATABASE = 'messages.db'

# --- Basic Anti-DDoS Rate Limiting ---
# Store the timestamp of the last request from each IP address.
# This is a simple in-memory solution. For a production environment,
# a more robust solution like Flask-Limiter with a Redis backend would be better.
request_counts = defaultdict(lambda: {'count': 0, 'last_request': 0})
RATE_LIMIT_SECONDS = 10  # Allow one request every 10 seconds
RATE_LIMIT_COUNT = 5 # Allow 5 requests in the time window

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT NOT NULL,
                content TEXT NOT NULL,
                avatar TEXT NOT NULL,
                top INTEGER NOT NULL,
                left_pos INTEGER NOT NULL
            )
        ''')
        conn.commit()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/messages', methods=['GET'])
def get_messages():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT id, author, content, avatar, top, left_pos as "left" FROM messages')
        messages = [dict(row) for row in cursor.fetchall()]
        return jsonify({'status': 'success', 'messages': messages})

@app.route('/api/messages', methods=['POST'])
def add_message():
    ip_address = request.remote_addr
    current_time = time.time()

    # Rate limiting check
    if current_time - request_counts[ip_address]['last_request'] < RATE_LIMIT_SECONDS:
        request_counts[ip_address]['count'] += 1
        if request_counts[ip_address]['count'] > RATE_LIMIT_COUNT:
            return jsonify({'status': 'error', 'message': 'Too many requests. Please wait a moment.'}), 429
    else:
        request_counts[ip_address]['count'] = 1
        request_counts[ip_address]['last_request'] = current_time

    data = request.get_json()
    
    author = data.get('author', 'Anonymous').strip()
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'status': 'error', 'message': 'Content cannot be empty'}), 400

    top = random.randint(15, 75)
    left_pos = random.randint(10, 70)
    avatar = f"https://api.dicebear.com/7.x/pixel-art/svg?seed={author or 'default'}"

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO messages (author, content, avatar, top, left_pos) VALUES (?, ?, ?, ?, ?)',
            (author if author else 'Anonymous', content, avatar, top, left_pos)
        )
        new_id = cursor.lastrowid
        conn.commit()

    new_msg = {
        'id': new_id,
        'author': author if author else 'Anonymous',
        'content': content,
        'avatar': avatar,
        'top': top,
        'left': left_pos
    }
    
    return jsonify({'status': 'success', 'message': new_msg})

if __name__ == '__main__':
    init_db()
    # Running on 0.0.0.0 makes the app accessible on your local network
    # using your IP address (e.g., http://192.168.68.56:5001)
    app.run(debug=True, port=5001, host='0.0.0.0')