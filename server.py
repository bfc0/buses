from __future__ import annotations
import logging
import anyio
import trio
import typing as t
import pydantic as p
from trio_websocket import serve_websocket, WebSocketRequest
from decorators import forever

T = t.TypeVar("T")


class Bus(p.BaseModel):
    busId: str
    lat: float = p.Field(ge=55.0, le=57.0)
    lng: float = p.Field(ge=36.0, le=39.0)
    route: str

    def is_inside(self, window: Window | None) -> bool:
        return window.contains(self) if window else False


class OutgoingMessage(p.BaseModel):
    msgType: str = "Buses"
    buses: list[Bus]


class Window(p.BaseModel):
    south_lat: float = p.Field(ge=50.0, le=60.0)
    north_lat: float = p.Field(ge=50.0, le=60.0)
    west_lng: float = p.Field(ge=30.0, le=40.0)
    east_lng: float = p.Field(ge=30.0, le=40.0)

    def contains(self, bus: Bus) -> bool:
        return (
            self.south_lat <= bus.lat <= self.north_lat
            and self.west_lng <= bus.lng <= self.east_lng
        )


class IncomingMessage(p.BaseModel):
    msgType: t.Literal["newBounds"]
    window: Window = p.Field(alias="data")


buses = {}


async def serve_browser(request: WebSocketRequest):
    ws = await request.accept()
    window = None

    @forever
    async def send():
        message = OutgoingMessage(
            buses=[bus for bus in buses.values() if bus.is_inside(window)])
        await ws.send_message(message.model_dump_json())
        await anyio.sleep(1)

    @forever
    async def receive():
        nonlocal window
        message = await ws.get_message()
        window = IncomingMessage.model_validate_json(message).window
        logging.info(f"window: {window}")

    async with trio.open_nursery() as nursery:
        nursery.start_soon(send)
        nursery.start_soon(receive)


async def get_buses(request: WebSocketRequest) -> None:
    ws = await request.accept()

    @forever
    async def _get_buses():
        try:
            raw_message = await ws.get_message()
            bus = Bus.model_validate_json(raw_message)
            buses[bus.busId] = bus
        except p.ValidationError as e:
            logging.error(f"message validation  failed: {
                e.errors()} message: {raw_message}")

    await _get_buses()


async def main():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve_websocket, serve_browser,
                           "127.0.0.1", 8000, None)

        nursery.start_soon(serve_websocket, get_buses,
                           "127.0.0.1", 8080, None)


if __name__ == "__main__":
    trio.run(main)
