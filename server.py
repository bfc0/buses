import trio
import json
import itertools
import typing as t
from trio_websocket import serve_websocket, ConnectionClosed

buses = {}


async def serve_browser(request):
    ws = await request.accept()

    while True:
        try:
            message = {
                "msgType": "Buses",
                "buses": [
                    msg for _, msg in buses.items()
                ], }
            # print(message)
            await ws.send_message(json.dumps(message, ensure_ascii=False))
            await trio.sleep(1)
        except ConnectionClosed:
            break


async def get_buses(request):
    ws = await request.accept()
    msg = {
        "msgType": "Buses",
        "buses": [
            {"busId": "c790сс", "lat": 55.7500, "lng": 37.600, "route": "120"},
            {"busId": "a134aa", "lat": 55.7494, "lng": 37.621, "route": "670к"},
        ],
    }

    while True:
        try:
            message = await ws.get_message()
            payload = json.loads(message)
            bus_id = payload["busId"]
            buses[bus_id] = payload

        except ConnectionClosed:
            break


async def main():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve_websocket, serve_browser,
                           "127.0.0.1", 8000, None)

        nursery.start_soon(serve_websocket, get_buses,
                           "127.0.0.1", 8080, None)


if __name__ == "__main__":
    trio.run(main)
