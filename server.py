import logging
import anyio
import trio
import json
import typing as t
import pydantic as p
from trio_websocket import serve_websocket, ConnectionClosed


class Bus(p.BaseModel):
    busId: str
    lat: float = p.Field(ge=55.0, le=57.0)
    lng: float = p.Field(ge=36.0, le=39.0)
    route: str


class OutgoingMessage(p.BaseModel):
    msgType: str
    buses: list[Bus]


buses = {}


async def serve_browser(request):
    ws = await request.accept()

    while True:
        try:
            message = OutgoingMessage(msgType="Buses", buses=buses.values())
            await ws.send_message(message.model_dump_json())
            await trio.sleep(1)
        except ConnectionClosed:
            break
        except Exception as e:
            logging.error(e)
            anyio.sleep(1)


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
            raw_message = await ws.get_message()
            bus = Bus.model_validate_json(raw_message)
            buses[bus.busId] = bus

        except ConnectionClosed:
            break
        except p.ValidationError as e:
            logging.error(f"message validation  failed: {
                          e.errors()} message: {raw_message}")

            continue


async def main():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve_websocket, serve_browser,
                           "127.0.0.1", 8000, None)

        nursery.start_soon(serve_websocket, get_buses,
                           "127.0.0.1", 8080, None)


if __name__ == "__main__":
    trio.run(main)
