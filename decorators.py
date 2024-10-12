import functools
import logging
import traceback
import typing as t
import anyio
from trio_websocket import ConnectionClosed


P = t.ParamSpec("P")


def forever(
    async_function: t.Callable[P, t.Awaitable[t.Any]]
) -> t.Callable[P, t.Awaitable[None]]:
    @functools.wraps(async_function)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        while True:
            try:
                await async_function(*args, **kwargs)
            except ConnectionClosed:
                logging.info("connection closed")
                break

    return wrapper


def reconnect(
    async_function: t.Callable[P, t.Awaitable[t.Any]]
) -> t.Callable[P, t.Awaitable[None]]:
    @functools.wraps(async_function)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        while True:
            try:
                await async_function(*args, **kwargs)
            except Exception as e:
                logging.error(e)
                logging.error(traceback.format_exc())
                await anyio.sleep(1)

    return wrapper
