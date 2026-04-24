from flask import Flask

app = Flask(__name__)
app.secret_key = 'chinese-chess-secret-key-2024'

from app import routes
