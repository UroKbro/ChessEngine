# server.py
from flask import Flask, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

players = {}  # sid -> 'white' | 'black'

@socketio.on('connect')
def handle_connect():
    if len(players) == 0:
        players[request.sid] = 'white'
        emit('color', {'color': 'white'})
        print("Player 1 connected as WHITE")
    elif len(players) == 1:
        players[request.sid] = 'black'
        emit('color', {'color': 'black'})
        print("Player 2 connected as BLACK")
    else:
        print("Room full, rejecting connection")
        return False  # reject

@socketio.on('disconnect')
def handle_disconnect():
    color = players.pop(request.sid, None)
    print(f"Player ({color}) disconnected")

@socketio.on('move')
def handle_move(data):
    print("Move received:", data)
    # Relay to the OTHER player only
    emit('move', data, broadcast=True, include_self=False)

if __name__ == '__main__':
    print("Chess server running on port 5000")
    print("Share your IP address with your friend to play!")
    socketio.run(app, host='0.0.0.0', port=5000)