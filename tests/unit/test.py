import websockets
import asyncio

async def test_ws():
    async with websockets.connect('ws://localhost:5000/tasks/cd4e137a-b62a-45dd-bb6f-6868f9fda187') as ws:
        try:
            while True:
                message = await ws.recv()
                print(message)
        except websockets.exceptions.ConnectionClosedOK:
            print("Connection closed by server.")

asyncio.get_event_loop().run_until_complete(test_ws())