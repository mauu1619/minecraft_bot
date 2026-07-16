import asyncio
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import aiomcrcon
from aiomcrcon.errors import (
    ClientNotConnectedError,
    IncorrectPasswordError,
    RCONConnectionError,
)
from loguru import logger
from mcstatus import JavaServer

from bot.exceptions import MinecraftBotError, RconConnectionError, ServerError


@dataclass(slots=True, frozen=True)
class RconCredentials:
    password: str
    host: str = "127.0.0.1"
    port: int = 25575

    def __repr__(self) -> str:
        return (
            f"RconCredentials(host={self.host!r}, port={self.port}"
            f"password={'***' if self.password else None})"
        )


@dataclass(slots=True)
class CommandResult:
    cmd: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


class ServerState(StrEnum):
    OFFLINE = "offline"
    STARTING = "starting"
    ONLINE = "online"


@dataclass(slots=True, frozen=True)
class ServerStatus:
    state: ServerState
    players_online: int = 0
    players_max: int = 0
    ping: int = 0


class ServerService:
    def __init__(
        self,
        rcon_creds: RconCredentials,
        server_dir: Path,
        service_name: str = "minecraft",
        game_port: int | None = None,
    ) -> None:
        self._rcon = rcon_creds
        self._systemd_service = service_name
        self._srv_path = server_dir
        self._server = JavaServer.lookup(
            f"127.0.0.1:{game_port or JavaServer.DEFAULT_PORT}"
        )

    async def _run_system_command(self, *args) -> CommandResult:
        process = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        cmd = " ".join(args)
        logger.debug("Выполнение системной команды '{}'", cmd)

        stdout, stderr = await process.communicate()

        return CommandResult(
            cmd=cmd,
            exit_code=process.returncode if process.returncode is not None else -1,
            stdout=stdout.decode().strip(),
            stderr=stderr.decode().strip(),
        )

    async def start_server(self) -> None:
        result = await self._run_system_command(
            "sudo", "systemctl", "start", self._systemd_service
        )
        if not result.ok:
            raise ServerError(f"Ошибка запуска (> {result.cmd}): {result.stderr}")

        logger.info("Служба {} запущена", self._systemd_service)

    async def stop_server(self) -> None:
        try:
            logger.debug("RCON-подключение: {}", self._rcon)

            async with aiomcrcon.Client(
                self._rcon.host, self._rcon.port, self._rcon.password
            ) as client:
                await client.connect()
                await client.send_cmd("say Сервер останавливается...")
                await asyncio.sleep(3)
                await client.send_cmd("save_all")
                await client.send_cmd("stop")
        except (
            ClientNotConnectedError,
            RCONConnectionError,
            IncorrectPasswordError,
        ) as exc:
            raise RconConnectionError(f"Ошибка подключения RCON: {exc}") from exc

        await asyncio.sleep(5)

        result = await self._run_system_command(
            "sudo", "systemctl", "stop", self._systemd_service
        )
        if not result.ok:
            raise ServerError(f"Ошибка запуска {result.cmd}: {result.stderr}")

        logger.info("Cлужба {} остановлена", self._systemd_service)

    async def restart_server(self) -> None:
        await self.stop_server()

        logger.info("Служба {} перезапущена", self._systemd_service)

        await self.start_server()

    async def _is_service_running(self) -> bool:
        result = await self._run_system_command(
            "systemctl", "is-active", "--quiet", self._systemd_service
        )

        return result.ok

    async def get_detailed_status(self) -> ServerStatus:
        is_running = await self._is_service_running()
        if not is_running:
            return ServerStatus(state=ServerState.OFFLINE)

        try:
            status = await self._server.async_status()

            return ServerStatus(
                state=ServerState.ONLINE,
                players_online=status.players.online,
                players_max=status.players.max,
                ping=round(status.latency),
            )
        except Exception:
            return ServerStatus(state=ServerState.STARTING)
