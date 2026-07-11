import asyncio

import aiomcrcon
from aiomcrcon.errors import (
    ClientNotConnectedError,
    IncorrectPasswordError,
    RCONConnectionError,
)

from bot.config import get_settings

settings = get_settings()


async def start_server() -> tuple[bool, str, str]:
    process = await asyncio.create_subprocess_exec(
        "sudo",
        "systemctl",
        "start",
        "minecraft",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )

    _, stderr = await process.communicate()

    return (
        process.returncode == 0,
        "",
        stderr.decode().strip(),
    )


async def stop_server() -> tuple[bool, str, str]:
    try:
        async with aiomcrcon.Client(
            "127.0.0.1", 25575, settings.rcon_password
        ) as client:
            await client.connect()
            await client.send_cmd("say Сервер останавливается...")
            await asyncio.sleep(1)
            await client.send_cmd("save_all")
            await client.send_cmd("stop")
    except (RCONConnectionError, ClientNotConnectedError, IncorrectPasswordError):
        pass

    await asyncio.sleep(5)

    process = await asyncio.create_subprocess_exec(
        "sudo",
        "systemctl",
        "stop",
        "minecraft",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )

    _, stderr = await process.communicate()

    return (
        process.returncode == 0,
        "",
        stderr.decode().strip(),
    )


async def restart_server() -> tuple[bool, str, str]:
    await stop_server()

    result, stdout, stderr = await start_server()

    return result, stdout, stderr
