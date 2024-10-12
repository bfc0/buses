from functools import partial
import json
import pytest
from trio_websocket import open_websocket_url, serve_websocket
from server import serve_browser, get_buses

bind_addr, port = "127.0.0.1", 9999


@pytest.fixture()
async def browser_socket(nursery):
    await nursery.start(partial(serve_websocket, serve_browser, bind_addr, port, None))
    async with open_websocket_url(f"ws://{bind_addr}:{port}") as ws:
        yield ws


@pytest.fixture()
async def bus_socket(nursery):
    await nursery.start(partial(serve_websocket, get_buses, bind_addr, port, None))
    async with open_websocket_url(f"ws://{bind_addr}:{port}") as ws:
        yield ws


async def test_newbounds_message_without_msgtype(browser_socket):
    await browser_socket.get_message()
    message = {
        "data": {"south_lat": 50, "north_lat": 50, "west_lng": 30, "east_lng": 30}
    }
    await browser_socket.send_message(json.dumps(message))
    response = json.loads(await browser_socket.get_message())
    assert response["msgType"] == "error"
    assert response["errors"][0]["type"] == "missing"
    assert response["errors"][0]["loc"] == ["msgType"]


async def test_newbounds_message_missing_south_lat(browser_socket):
    await browser_socket.get_message()
    message = {
        "msgType": "newBounds",
        "data": {"north_lat": 50, "west_lng": 30, "east_lng": 30},
    }
    await browser_socket.send_message(json.dumps(message))
    response = json.loads(await browser_socket.get_message())
    assert response["msgType"] == "error"
    assert response["errors"][0]["type"] == "missing"
    assert response["errors"][0]["loc"] == ["data", "south_lat"]


async def test_newbounds_message_oob_south_lat(browser_socket):
    await browser_socket.get_message()
    message = {
        "msgType": "newBounds",
        "data": {"north_lat": 50, "south_lat": 20, "west_lng": 30, "east_lng": 30},
    }
    await browser_socket.send_message(json.dumps(message))
    response = json.loads(await browser_socket.get_message())
    assert response["msgType"] == "error"
    assert response["errors"][0]["type"] == "greater_than_equal"
    assert response["errors"][0]["loc"] == ["data", "south_lat"]


async def test_correct_bus_message(bus_socket):
    message = {
        "busId": "123",
        "lat": 55.0,
        "lng": 37.0,
        "route": "123",
    }

    await bus_socket.send_message(json.dumps(message))
    response = json.loads(await bus_socket.get_message())
    assert response == {"msgType": "ok"}


async def test_bus_message_with_missing_bus_id(bus_socket):
    message = {
        "lat": 55.0,
        "lng": 37.0,
        "route": "123",
    }

    await bus_socket.send_message(json.dumps(message))
    response = json.loads(await bus_socket.get_message())
    assert response["msgType"] == "error"
    assert response["errors"][0]["type"] == "missing"
    assert response["errors"][0]["loc"] == ["busId"]


async def test_bus_message_with_incorrect_lat(bus_socket):
    message = {
        "busId": "123",
        "lat": 49.0,
        "lng": 37.0,
        "route": "123",
    }

    await bus_socket.send_message(json.dumps(message))
    response = json.loads(await bus_socket.get_message())
    assert response["msgType"] == "error"
    assert response["errors"][0]["type"] == "greater_than_equal"
    assert response["errors"][0]["loc"] == ["lat"]
