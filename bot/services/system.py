import asyncio


async def is_server_running(service_name: str = "minecraft") -> bool:
    process = await asyncio.create_subprocess_exec(
        "systemctl",
        "is-active",
        "--quiet",
        service_name,
    )

    await process.communicate()

    return process.returncode == 0
