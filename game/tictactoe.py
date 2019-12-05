import asyncio
import uuid
import json

from functools import wraps
from quart import Quart, websocket, request, jsonify, session
from quart.templating import render_template


### App Setup ###

app = Quart(__name__)
app.secret_key = 'very_secret'

connected_websockets = set()
games = []
users = dict()


### Game Logic ###

class Game:
    '''Tic Tac Toe game class holding the game state and rules.'''

    def __init__(self, player1, player2, *args, **kwargs):
        self.player1 = player1
        self.player2 = player2
        self.turn = self.player1
        self.board = [None] * 9

    def move(self, player, location):
        if self.result() is not None:
            raise Exception('game over!')
        if player != self.turn:
            raise Exception('its not your turn!')
        if self.board[location] is not None:
            raise Exception('invalid move')

        self.board[location] = player

        if player != self.player1:
            self.turn = self.player1
        else:
            self.turn = self.player2

    def result(self):
        wins = [
            [0, 1, 2],
            [3, 4, 5],
            [6, 7, 8],
            [0, 3, 6],
            [1, 4, 7],
            [2, 5, 8],
            [0, 4, 8],
            [2, 4, 6],
        ]

        # check for winner
        for w in wins:
            if self.board[w[0]] == self.board[w[1]] == self.board[w[2]] != None:
                return self.board[w[0]]

        # check for draw
        if all(self.board):
            return 'draw'
        else:
            return None

    def to_json(self):
        return dict(
            player1 = self.player1,
            player2 = self.player2,
            turn = self.turn,
            result = self.result(),
            board = self.board,
        )


class GameJSONEncoder(json.JSONEncoder):
    '''JSON Encoder for game class.'''

    def default(self, object_):
        if isinstance(object_, Game):
            return object_.to_json()
        else:
            return super().default(object_)


app.json_encoder = GameJSONEncoder


### Endpoints and Utils ###

def get_users():
    '''Return users in a format suitable for front end.'''
    return [dict(id=k, name=v) for k, v in users.items()]


def broadcast(message):
    '''Send message to all other websockets, who are pulling from their queues.'''
    for queue in connected_websockets:
        queue.put_nowait(message)


def user_required(func):
    '''Wrapper to make sure user has an id, broadcasts new users who join.'''
    @wraps(func)
    def wrapper(*args, **kwargs):
        global users
        if 'id' not in session:
            session['id'] = uuid.uuid4().hex[:5]
        if session['id'] not in users:
            users[session['id']] = ''

            # notify all players
            broadcast(dict(users=get_users()))

        return func(*args, **kwargs)
    return wrapper


@app.route('/')
@user_required
def index():
    return render_template('index.html')


@app.route('/api/games')
@user_required
def list_games():
    return jsonify(dict(games=games))


@app.route('/api/username', methods=['POST'])
@user_required
async def update_username():
    body = await request.json
    users[session['id']] = body.get('username')

    # notify all players
    broadcast(dict(users=get_users()))

    return 'success', 200


@app.route('/api/games', methods=['POST'])
@user_required
async def create_game():
    body = await request.json
    player1 = session['id']
    player2 = body.get('player')

    if player1 == player2:
        return 'can\'t play yourself!', 403

    new_game = Game(player1, player2)
    games.append(new_game)

    # notify all players
    broadcast(dict(games=games))

    return jsonify(games)


@app.route('/api/games/<int:game_id>')
@user_required
def get_game(game_id):
    try:
        return jsonify(games[game_id])
    except IndexError:
        return 'Game id not found', 404


@app.route('/api/games/<int:game_id>', methods=['POST'])
@user_required
async def move_game(game_id):
    body = await request.json
    try:
        game = games[game_id]
    except IndexError:
        return 'Game id not found', 404

    player = session['id']
    location = body.get('location')

    try:
        game.move(player, location)
    except Exception as e:
        return str(e), 401

    # notify all players
    broadcast(dict(games=games))

    return jsonify(game)


### Websocket Endpoint ###

def collect_websocket(func):
    '''Wrapper to register all websocket connections.'''
    @wraps(func)
    async def wrapper(*args, **kwargs):
        global connected_websockets
        queue = asyncio.Queue()
        connected_websockets.add(queue)
        try:
            return await func(queue, *args, **kwargs)
        finally:
            connected_websockets.remove(queue)
    return wrapper


@app.websocket('/listen')
@collect_websocket
async def listen(queue):
    '''Endpoint to broadcast queue messages to websocket connections.'''

    # send initial state when first listening
    await websocket.send(json.dumps(
        dict(userId=session['id'], games=games, users=get_users()),
        cls=GameJSONEncoder
    ))
    while True:
        # read from this websocket's queue and send
        data = await queue.get()
        await websocket.send(json.dumps(data, cls=GameJSONEncoder))
