from functools import partial
import json
import pytest
from trio_websocket import open_websocket_url, serve_websocket
from server import serve_browser

bind_addr, port = "127.0.0.1", 9999


@pytest.fixture()
async def browser_socket(nursery):
    server = await nursery.start(
        partial(serve_websocket, serve_browser, bind_addr, port, None)
    )
    async with open_websocket_url(f"ws://{bind_addr}:{port}") as ws:
        yield ws


async def test_correct_newbounds_message(browser_socket):
    await browser_socket.get_message()
    message = {"msgType": "newBounds", "data": {
        "south_lat": 50, "north_lat": 50, "west_lng": 30, "east_lng": 30}}
    await browser_socket.send_message(json.dumps(message))
    response = await browser_socket.get_message()
    assert response == json.dumps({"msgType": "ok"})


async def test_newbounds_message_without_msgtype(browser_socket):
    await browser_socket.get_message()
    message = {"data": {
        "south_lat": 50, "north_lat": 50, "west_lng": 30, "east_lng": 30}}
    await browser_socket.send_message(json.dumps(message))
    response = json.loads(await browser_socket.get_message())
    assert response["msgType"] == "error"
    assert response["errors"][0]["type"] == "missing"
    assert response["errors"][0]["loc"] == ["msgType"]


async def test_newbounds_message_missing_south_lat(browser_socket):
    await browser_socket.get_message()
    message = {"msgType": "newBounds", "data": {
        "north_lat": 50, "west_lng": 30, "east_lng": 30}}
    await browser_socket.send_message(json.dumps(message))
    response = json.loads(await browser_socket.get_message())
    assert response["msgType"] == "error"
    assert response["errors"][0]["type"] == "missing"
    assert response["errors"][0]["loc"] == ["data", "south_lat"]


async def test_newbounds_message_out_of_bounds_north_lat(browser_socket):
    await browser_socket.get_message()
    message = {"msgType": "newBounds", "data": {
        "north_lat": 70, "south_lat": 50, "west_lng": 30, "east_lng": 30}}
    await browser_socket.send_message(json.dumps(message))
    response = json.loads(await browser_socket.get_message())
    assert response["msgType"] == "error"
    assert response["errors"][0]["type"] == "less_than_equal"
    assert response["errors"][0]["loc"] == ["data", "north_lat"]
