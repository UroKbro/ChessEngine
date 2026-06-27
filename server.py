# server.py
import os
from flask import Flask, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

PORT = int(os.environ.get("CHESS_SERVER_PORT", "5000"))

players = {}  # sid -> 'white' | 'black'
clock_state = {
    'whiteTime': 10 * 60.0,
    'blackTime': 10 * 60.0,
    'activeColor': 'white',
}

@socketio.on('connect')
def handle_connect():
    assigned_colors = set(players.values())

    if 'white' not in assigned_colors:
        players[request.sid] = 'white'
        emit('color', {'color': 'white'})
        print("Player 1 connected as WHITE")
    elif 'black' not in assigned_colors:
        players[request.sid] = 'black'
        emit('color', {'color': 'black'})
        print("Player 2 connected as BLACK")
    else:
        print("Room full, rejecting connection")
        return False  # reject

    emit('state', clock_state)

@socketio.on('disconnect')
def handle_disconnect():
    color = players.pop(request.sid, None)
    print(f"Player ({color}) disconnected")

@socketio.on('move')
def handle_move(data):
    print("Move received:", data)
    active = clock_state['activeColor']
    if active == 'white':
        clock_state['whiteTime'] = max(0.0, float(data.get('whiteTime', clock_state['whiteTime'])))
        clock_state['blackTime'] = max(0.0, float(data.get('blackTime', clock_state['blackTime'])))
        clock_state['activeColor'] = 'black'
    else:
        clock_state['whiteTime'] = max(0.0, float(data.get('whiteTime', clock_state['whiteTime'])))
        clock_state['blackTime'] = max(0.0, float(data.get('blackTime', clock_state['blackTime'])))
        clock_state['activeColor'] = 'white'
    # Relay to the OTHER player only
    emit('move', data, broadcast=True, include_self=False)
    emit('state', clock_state, broadcast=True)

if __name__ == '__main__':
    print(f"Chess server running on port {PORT}")
    print("Share your IP address with your friend to play!")
    socketio.run(app, host='0.0.0.0', port=PORT, allow_unsafe_werkzeug=True)
