import asyncio
import json

from functools import wraps
from quart import Quart, websocket, request, jsonify, session


app = Quart(__name__)
connected_websockets = set()


def collect_websocket(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        global connected_websockets
        queue = asyncio.Queue()
        connected_websockets.add(queue)
        print('adding websocket queue, total size now', len(connected_websockets))
        try:
            return await func(queue, *args, **kwargs)
        finally:
            connected_websockets.remove(queue)
            print('removed websocket queue, total size now', len(connected_websockets))

    return wrapper


games = []

class Game:

    def __init__(self, player1, player2, *args, **kwargs):
        self.player1 = player1
        self.player2 = player2
        self.board = [None] * 9

    def move(self, player, location):
        if self.board[location] is not None:
            raise Exception('invalid move')
        if self.result is not None:
            raise Exception('game over!')

        self.board[location] = player

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
            result = self.result(),
            board = self.board,
        )


class GameJSONEncoder(json.JSONEncoder):

    def default(self, object_):
        if isinstance(object_, Game):
            return object_.to_json()
        else:
            return super().default(object_)


app.json_encoder = GameJSONEncoder


@app.route('/')
async def index():
    return games


@app.route('/api/games')
async def list_games():
    return jsonify(games)


@app.route('/api/games', methods=['POST'])
async def create_game():
    body = await request.json
    player1 = body.get('player1')
    player2 = body.get('player2')
    new_game = Game(player1, player2)
    games.append(new_game)
    return jsonify(games)


@app.route('/api/games/<int:game_id>')
async def get_game(game_id):
    try:
        return jsonify(games[game_id])
    except IndexError:
        return 'Game id not found', 404


@app.route('/api/games/<int:game_id>', methods=['POST'])
async def move_game(game_id):
    try:
        game = games[game_id]
    except IndexError:
        return 'Game id not found', 404

    body = await request.json
    player = body.get('player')
    location = body.get('location')
    try:
        game.move(player, location)
    except Exception:
        return 'Invalid Move', 401

    return jsonify(game)


async def broadcast(message):
    # send message to all other websockets, who are pulling from their queues
    print('length of connected sockets', len(connected_websockets))
    for queue in connected_websockets:
        await queue.put(message)


@app.websocket('/ws')
async def ws():
    while True:
        data = await websocket.receive()
        print(f'received data {data}')

        await broadcast(data)
        print('queued data!')


@app.websocket('/listen')
@collect_websocket
async def listen(queue):
    await websocket.send(f'connected!')
    while True:
        # read from this websocket's queue
        data = await queue.get()
        await websocket.send(f'echo {data}')
