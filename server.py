from __future__ import annotations
import json
import logging
import anyio
import trio
import typing as t
import pydantic as p
import asyncclick as click
from contextlib import suppress
from trio_websocket import ConnectionClosed, serve_websocket, WebSocketRequest
from decorators import forever


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
            buses=[bus for bus in buses.values() if bus.is_inside(window)]
        )
        await ws.send_message(message.model_dump_json())
        await anyio.sleep(1)

    @forever
    async def receive():
        nonlocal window
        message = await ws.get_message()
        try:
            window = IncomingMessage.model_validate_json(message).window
            logging.info(f"window: {window}")
        except p.ValidationError as e:
            logging.error(
                f"message validation  failed: {
                    e.errors()} message: {message}"
            )
            await ws.send_message(
                json.dumps({"msgType": "error", "errors": e.errors()})
            )

    async with trio.open_nursery() as nursery:
        nursery.start_soon(send)
        nursery.start_soon(receive)


async def get_buses(request: WebSocketRequest) -> None:
    ws = await request.accept()

    @forever
    async def _get_buses():
        global buses
        try:
            raw_message = await ws.get_message()
            bus = Bus.model_validate_json(raw_message)
            buses[bus.busId] = bus
            await ws.send_message(json.dumps({"msgType": "ok"}))
        except p.ValidationError as e:
            logging.error(
                f"message validation  failed: {
                    e.errors()} message: {raw_message}"  # type:ignore
            )
            await ws.send_message(
                json.dumps({"msgType": "error", "errors": e.errors()})
            )
        except ConnectionClosed:
            buses = {}
            raise

    await _get_buses()


@click.command()
@click.option("--host", default="127.0.0.1", help="Server Host")
@click.option("--buses_port", default=8080, help="Buses Port")
@click.option("--browser_port", default=8000, help="Browser Port")
@click.option(
    "--log_level",
    "-l",
    type=click.Choice(["debug", "info", "warning", "error", "critical"]),
    default="info",
    show_default=True,
    help="Set logging level",
)
async def main(host, buses_port, browser_port, log_level):
    logging.basicConfig(level=log_level.upper())
    logging.debug("starting server")
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve_websocket, serve_browser, host, browser_port, None)
        nursery.start_soon(serve_websocket, get_buses, host, buses_port, None)


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        main(_anyio_backend="trio")
