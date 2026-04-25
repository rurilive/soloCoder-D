from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = 'chat-system-secret-key-2024'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

from app import routes, chat
