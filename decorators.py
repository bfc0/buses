import functools
import logging
import traceback
import typing as t
import anyio
from trio_websocket import ConnectionClosed

T = t.TypeVar("T")


def forever(func: t.Callable[..., t.Awaitable[T]]) -> t.Callable[..., t.Awaitable[T]]:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        while True:
            try:
                await func(*args, **kwargs)
            except ConnectionClosed:
                logging.info("connection closed")
                break
    return wrapper


def reconnect(async_function: t.Callable[..., t.Awaitable[T]]) -> t.Callable[..., t.Awaitable[T]]:
    @functools.wraps(async_function)
    async def wrapper(*args, **kwargs):
        while True:
            try:
                await async_function(*args, **kwargs)
            except Exception as e:
                logging.error(e)
                logging.error(traceback.format_exc())
                await anyio.sleep(1)

    return wrapper
