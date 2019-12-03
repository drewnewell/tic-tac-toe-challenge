import asyncio

from functools import wraps
from quart import Quart, websocket


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

    return wrapper


@app.route('/')
async def index():
    return 'Hello World'


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
    while True:
        # read from this websocket's queue
        response = await queue.get()
        await websocket.send(f'echo {response}')
