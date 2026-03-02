"""Simple live scoreboard application.

Provides a Flask + Flask-SocketIO server that tracks multiple games
in an SQLite database. Real-time score updates are broadcast to all
clients viewing the same game ID. Includes REST endpoints for game
state, creation, and listing, plus utility functions for database
operations.

Run the server with:

    python app.py --port 6050

"""

from flask import Flask, render_template, request, jsonify, redirect
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import os
import json
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

DB_PATH = os.path.join(os.path.dirname(__file__), 'score.db')
LOG_PATH = os.path.join(os.path.dirname(__file__), 'changes.log')


def log_event(event: str, data: dict):
    """Append a JSON-line event to the changes.log file with an ISO timestamp."""
    entry = {
        'ts': datetime.utcnow().isoformat() + 'Z',
        'event': event,
        'data': data
    }
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception:
        # avoid crashing on logging errors
        pass


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Check for games table (new schema)
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
    if c.fetchone():
        # games table exists, nothing to do
        conn.commit()
        conn.close()
        return

    # Create new games table
    c.execute('''
        CREATE TABLE games (
            id TEXT PRIMARY KEY,
            game_name TEXT NOT NULL,
            game_date TEXT NOT NULL,
            team1_name TEXT NOT NULL DEFAULT 'team1',
            team2_name TEXT NOT NULL DEFAULT 'team2',
            team1_score INTEGER NOT NULL DEFAULT 0,
            team2_score INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')

    # Create a test game for basic functionality
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute('''
        INSERT INTO games (id, game_name, game_date, team1_name, team2_name, team1_score, team2_score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('test', 'Test Game', today, 'team1', 'team2', 0, 0, datetime.utcnow().isoformat() + 'Z'))

    conn.commit()
    conn.close()
    log_event('db_initialized', {'path': DB_PATH, 'test_game_created': True})


def get_state(game_id: str = 'default'):
    """Fetch the state of a specific game."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT game_name, game_date, team1_name, team2_name, team1_score, team2_score FROM games WHERE id = ?', (game_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'game_id': game_id,
        'game_name': row[0],
        'game_date': row[1],
        'team1_name': row[2],
        'team2_name': row[3],
        'team1_score': row[4],
        'team2_score': row[5]
    }


def set_team_name(game_id: str, team_index: int, name: str):
    """Update team name in a specific game."""
    col = 'team1_name' if team_index == 1 else 'team2_name'
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f'UPDATE games SET {col} = ? WHERE id = ?', (name, game_id))
    conn.commit()
    conn.close()
    # log the name change
    try:
        state = get_state(game_id)
        log_event('name_changed', {'game_id': game_id, 'team': team_index, 'name': name, 'state': state})
    except Exception:
        pass


def change_team_score(game_id: str, team_index: int, delta: int = 0, value: int = None):
    """Update team score in a specific game."""
    if value is not None:
        # set absolute value
        col = 'team1_score' if team_index == 1 else 'team2_score'
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(f'UPDATE games SET {col} = ? WHERE id = ?', (int(value), game_id))
        conn.commit()
        conn.close()
        return

    # apply delta
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if team_index == 1:
        c.execute('UPDATE games SET team1_score = team1_score + ? WHERE id = ?', (int(delta), game_id))
    else:
        c.execute('UPDATE games SET team2_score = team2_score + ? WHERE id = ?', (int(delta), game_id))
    conn.commit()
    conn.close()
    # log the score change
    try:
        state = get_state(game_id)
        log_event('score_changed', {'game_id': game_id, 'team': team_index, 'delta': int(delta), 'state': state})
    except Exception:
        pass


def set_game_metadata(game_id: str, game_name: str = None, game_date: str = None):
    """Update game name and/or date."""
    updates = []
    params = []
    if game_name:
        updates.append('game_name = ?')
        params.append(game_name)
    if game_date:
        updates.append('game_date = ?')
        params.append(game_date)
    if not updates:
        return
    params.append(game_id)
    stmt = 'UPDATE games SET ' + ', '.join(updates) + ' WHERE id = ?'
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(stmt, params)
    conn.commit()
    conn.close()
    # log the metadata change
    try:
        state = get_state(game_id)
        log_event('game_metadata_changed', {'game_id': game_id, 'game_name': game_name, 'game_date': game_date, 'state': state})
    except Exception:
        pass


def reset_game_scores(game_id: str):
    """Reset both team scores to 0 for a game."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE games SET team1_score = 0, team2_score = 0 WHERE id = ?', (game_id,))
    conn.commit()
    conn.close()
    try:
        state = get_state(game_id)
        log_event('game_reset', {'game_id': game_id, 'state': state})
    except Exception:
        pass


@app.route('/')
def index():
    """
    Root route: generate a new random game ID and redirect to its setup page.
    This ensures each new visitor starts with a fresh game.
    """
    import random
    import string
    # Generate a random 8-character game ID
    game_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return redirect(f'/game/{game_id}')


@app.route('/game/<game_id>')
def game(game_id: str):
    """Serve the scoreboard for a specific game."""
    # Always serve the HTML template; let frontend check if game exists
    # and show setup modal if needed
    return render_template('index.html')


@app.route('/api/games', methods=['GET'])
def api_games():
    """List all games."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, game_name, game_date FROM games ORDER BY created_at DESC')
    games = [{'id': row[0], 'game_name': row[1], 'game_date': row[2]} for row in c.fetchall()]
    conn.close()
    return jsonify(games)


@app.route('/api/game/<game_id>', methods=['GET'])
def api_game(game_id: str):
    """Get state of a specific game."""
    state = get_state(game_id)
    if not state:
        return {"error": "Game not found"}, 404
    return jsonify(state)


@app.route('/api/game/<game_id>/exists', methods=['GET'])
def api_game_exists(game_id: str):
    """Check if a game exists."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id FROM games WHERE id = ?', (game_id,))
    exists = c.fetchone() is not None
    conn.close()
    return jsonify({'exists': exists})


@app.route('/api/game/create/<game_id>', methods=['POST'])
def api_create_game(game_id: str):
    """Create a new game with the given ID and metadata."""
    data = request.get_json() or {}
    game_name = data.get('game_name', 'Unnamed Game')
    game_date = data.get('game_date', datetime.now().strftime('%Y-%m-%d'))
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check if game already exists
    c.execute('SELECT id FROM games WHERE id = ?', (game_id,))
    if c.fetchone():
        conn.close()
        return jsonify({'error': 'Game already exists'}), 409
    
    # Create new game
    c.execute('''
        INSERT INTO games (id, game_name, game_date, team1_name, team2_name, team1_score, team2_score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (game_id, game_name, game_date, 'team1', 'team2', 0, 0, datetime.utcnow().isoformat() + 'Z'))
    conn.commit()
    conn.close()
    
    state = get_state(game_id)
    log_event('game_created', {'game_id': game_id, 'game_name': game_name, 'game_date': game_date})
    return jsonify(state), 201


@socketio.on('connect')
def handle_connect(auth):
    # Get game_id from query params or default
    game_id = request.args.get('game_id', 'default')
    # Join the game-specific room
    join_room(f'game_{game_id}')
    state = get_state(game_id)
    if state:
        emit('state_update', state)


@socketio.on('change_score')
def handle_change_score(data):
    # data: {game_id: 'abc', team: 1|2, delta: 1 or -1}
    try:
        game_id = data.get('game_id', 'default')
        team = int(data.get('team', 1))
        if 'delta' in data:
            change_team_score(game_id, team, delta=int(data['delta']))
        elif 'value' in data:
            change_team_score(game_id, team, value=int(data['value']))
        else:
            return
        state = get_state(game_id)
        if state:
            emit('state_update', state, broadcast=True, to=f'game_{game_id}')
    except Exception as e:
        print('error changing team score', e)


@socketio.on('set_name')
def handle_set_name(data):
    # data: {game_id: 'abc', team: 1|2, name: 'New Name'}
    try:
        game_id = data.get('game_id', 'default')
        team = int(data.get('team', 1))
        name = str(data.get('name', '')).strip()
        if name == '':
            return
        set_team_name(game_id, team, name)
        state = get_state(game_id)
        if state:
            emit('state_update', state, broadcast=True, to=f'game_{game_id}')
    except Exception as e:
        print('error setting team name', e)


@socketio.on('set_game_metadata')
def handle_set_metadata(data):
    # data: {game_id: 'abc', game_name: 'Friendly', game_date: '2026-03-02'}
    try:
        game_id = data.get('game_id', 'default')
        game_name = data.get('game_name')
        game_date = data.get('game_date')
        set_game_metadata(game_id, game_name, game_date)
        state = get_state(game_id)
        if state:
            emit('state_update', state, broadcast=True, to=f'game_{game_id}')
    except Exception as e:
        print('error setting game metadata', e)


@socketio.on('reset_scores')
def handle_reset_scores(data):
    # data: {game_id: 'abc'}
    try:
        game_id = data.get('game_id', 'default')
        reset_game_scores(game_id)
        state = get_state(game_id)
        if state:
            emit('state_update', state, broadcast=True, to=f'game_{game_id}')
    except Exception as e:
        print('error resetting game scores', e)


if __name__ == '__main__':
    init_db()
    # command-line options for host/port with env var fallback
    import argparse
    parser = argparse.ArgumentParser(description='Run scoreboard server')
    parser.add_argument('--host', default=os.environ.get('HOST', '0.0.0.0'),
                        help='Host interface to bind to')
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 6050)),
                        help='Port to listen on')
    args = parser.parse_args()
    socketio.run(app, host=args.host, port=args.port)
