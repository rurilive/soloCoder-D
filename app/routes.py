from flask import render_template, request, jsonify, send_from_directory
from app import app
import os
import uuid
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('visitor.html')

@app.route('/agent')
def agent():
    return render_template('agent.html')

@app.route('/embed.js')
def embed_script():
    return app.send_static_file('js/embed.js')

@app.route('/chat')
def chat_demo():
    return render_template('visitor.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        new_filename = f"{uuid.uuid4()}.{file_ext}" if file_ext else str(uuid.uuid4())
        
        file_path = os.path.join(UPLOAD_FOLDER, new_filename)
        file.save(file_path)
        
        file_size = os.path.getsize(file_path)
        
        return jsonify({
            'success': True,
            'file_name': original_filename,
            'file_path': f'/uploads/{new_filename}',
            'file_size': file_size
        })
    
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/api/emojis')
def get_emojis():
    emojis = [
        '😀', '😂', '🥰', '😎', '🤔', '👍', '👎', '❤️',
        '🔥', '🎉', '😢', '😡', '🙏', '👋', '✨', '💯'
    ]
    return jsonify({'emojis': emojis})
