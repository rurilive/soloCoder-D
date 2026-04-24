from flask import render_template, request, jsonify, redirect, url_for, session
from app import app
from app.chess.game import Game
from app.chess.pieces import Color
from app.chess.ai import Difficulty
import uuid
import traceback

games = {}

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Unhandled exception: {e}")
    app.logger.error(traceback.format_exc())
    if request.path.startswith('/api/'):
        return jsonify({'error': str(e), 'success': False}), 500
    return render_template('index.html'), 500

def get_or_create_game() -> Game:
    game_id = session.get('game_id')
    if game_id is None or game_id not in games:
        game_id = str(uuid.uuid4())
        session['game_id'] = game_id
        games[game_id] = Game()
    return games[game_id]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/game')
def game():
    return render_template('game.html')

@app.route('/api/start', methods=['POST'])
def start_game():
    data = request.get_json()
    player_color_str = data.get('player_color', 'red')
    difficulty_str = data.get('difficulty', 'medium')

    player_color = Color(player_color_str)
    difficulty = Difficulty(difficulty_str)

    game = get_or_create_game()
    game.start_game(player_color, difficulty)

    return jsonify(game.get_game_state())

@app.route('/api/state')
def get_state():
    game = get_or_create_game()
    return jsonify(game.get_game_state())

@app.route('/api/select', methods=['POST'])
def select_piece():
    data = request.get_json()
    row = data.get('row')
    col = data.get('col')

    game = get_or_create_game()
    success = game.select_piece(row, col)

    return jsonify({
        'success': success,
        'state': game.get_game_state()
    })

@app.route('/api/move', methods=['POST'])
def make_move():
    data = request.get_json()
    from_row = data.get('from_row')
    from_col = data.get('from_col')
    to_row = data.get('to_row')
    to_col = data.get('to_col')

    game = get_or_create_game()
    success = game.make_move(from_row, from_col, to_row, to_col)

    return jsonify({
        'success': success,
        'state': game.get_game_state()
    })

@app.route('/api/share')
def share_game():
    game = get_or_create_game()
    share_code = game.get_share_code()
    share_url = url_for('replay', share_code=share_code, _external=True)
    return jsonify({
        'share_code': share_code,
        'share_url': share_url
    })

@app.route('/replay/<share_code>')
def replay(share_code):
    game = get_or_create_game()
    replay_steps = game.load_replay(share_code)

    if not replay_steps:
        return redirect(url_for('index'))

    return render_template('replay.html', replay_steps=replay_steps, share_code=share_code)

@app.route('/api/replay/<share_code>')
def get_replay_data(share_code):
    game = get_or_create_game()
    replay_steps = game.load_replay(share_code)

    if not replay_steps:
        return jsonify({'error': 'Invalid share code'}), 400

    steps_data = []
    for step_name, board_state in replay_steps:
        steps_data.append({
            'name': step_name,
            'board': board_state['board'],
            'last_move': board_state.get('last_move')
        })

    return jsonify({'steps': steps_data})

@app.route('/api/continue', methods=['POST'])
def continue_game():
    data = request.get_json()
    share_code = data.get('share_code')

    game = Game.from_share_code(share_code)
    if game is None:
        return jsonify({'error': 'Invalid share code'}), 400

    game_id = str(uuid.uuid4())
    session['game_id'] = game_id
    games[game_id] = game

    return jsonify(game.get_game_state())
