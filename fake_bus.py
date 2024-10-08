import os
import itertools
import json
import logging
import traceback
import trio
import anyio
import typing as t
import random
import functools
import asyncclick as click
from trio_websocket import open_websocket_url
from decorators import reconnect

T = t.TypeVar("T")


def load_routes(directory_path="routes") -> t.Generator[dict, None, None]:
    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, "r", encoding="utf8") as file:
                yield json.load(file)


async def run_bus(
    channel: trio.MemorySendChannel,
    bus_id: str,
    route_name: str,
    coordinates: list[tuple[float, float]],
):
    for lat, lng in itertools.cycle(coordinates):
        message = json.dumps(
            {
                "busId": bus_id,
                "lat": lat,
                "lng": lng,
                "route": route_name,
            },
            ensure_ascii=False,
        )
        await channel.send(message)
        await anyio.sleep(1)


def create_runner(
    route: dict[str, t.Any], channel: trio.MemorySendChannel
) -> functools.partial[t.Awaitable[None]]:
    coordinates = route["coordinates"]
    offset = random.randint(0, len(coordinates) - 1)
    bus_id = f"bus-{route['name']}-{offset}"
    coordinates = coordinates[offset:] + coordinates[:offset]
    return functools.partial(run_bus, channel, bus_id, route["name"], coordinates)


@reconnect
async def retranslate_to_server(recv_chan: trio.MemoryReceiveChannel, url: str):
    async with open_websocket_url(url) as ws:
        async for message in recv_chan:
            await ws.send_message(message)


@click.command()
@click.option("--url", default="ws://localhost:8080", help="Server URL")
@click.option("--sockets", default=5, help="Number of sockets")
@click.option("--buses_per_route", default=10, help="Number of buses per route")
async def main(url, sockets, buses_per_route):
    try:
        routes = load_routes()
        channels = [trio.open_memory_channel(0) for _ in range(sockets)]
        async with trio.open_nursery() as nursery:
            for route in routes:
                for _ in range(buses_per_route):
                    random_channel, _ = random.choice(channels)
                    bus_runner = create_runner(route, random_channel)
                    nursery.start_soon(bus_runner)

            for _, recv_chan in channels:
                nursery.start_soon(retranslate_to_server, recv_chan, url)

    except Exception as e:
        await anyio.sleep(1)
        logging.error(e)
        logging.error(traceback.format_exc())


if __name__ == "__main__":
    # trio.run(main)
    main(_anyio_backend="trio")
