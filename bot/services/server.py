import asyncio
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import StrEnum
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, TypeAlias, TypeVar

import aiomcrcon
from aiomcrcon.errors import (
    ClientNotConnectedError,
    IncorrectPasswordError,
    RCONConnectionError,
)
from loguru import logger
from mcstatus import JavaServer

from bot.exceptions import MinecraftBotError, RCONError, ServerError

MAX_RCON_CMD_LEN = 1446

RCONCommand: TypeAlias = str | int | float
T = TypeVar("T")
P = ParamSpec("P")


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


@dataclass(slots=True, kw_only=True)
class CommandResult:
    cmd: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


@dataclass(slots=True, kw_only=True)
class RCONResult:
    cmd: str
    response: str
    req_id: int


@dataclass(slots=True)
class RCONResults:
    rcon_results: list[RCONResult]


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


class RetryOnRCONError:
    def __init__(self, retries: int = 3, delay: float = 2) -> None:
        if retries <= 0:
            raise ValueError("Количество попыток должно быть больше нуля")
        if delay < 0:
            raise ValueError("Задержка не может быть отрицательной")

        self.retries = retries
        self.delay = delay

    def __call__(
        self, func: Callable[P, Coroutine[Any, Any, T]]
    ) -> Callable[P, Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            for attempt in range(1, self.retries + 1):
                try:
                    return await func(*args, **kwargs)

                except IncorrectPasswordError as exc:
                    raise RCONError("Ошибка авторизации RCON: неверный пароль") from exc

                except ClientNotConnectedError as exc:
                    raise RCONError("RCON соединение не было установлено") from exc

                except (RCONConnectionError, ValueError) as exc:
                    if attempt == self.retries:
                        logger.error(
                            f"RCON недоступен после {self.retries} попыток: {exc}"
                        )
                        raise ServerError(
                            "Сервер Minecraft недоступен или не отвечает. Повторите позже"
                        ) from exc

                    logger.warning(
                        f"Сбой RCON (попытка {attempt}/{self.retries}). Повтор через {self.delay}s"
                    )
                    await asyncio.sleep(self.delay)

            assert False

        return wrapper


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
        """
        *args = ("cmd_part1", "cmd_part2", "cmd_part3", ...)
        Каждый аргумент - это часть целой команды
        """
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

    @RetryOnRCONError(retries=3, delay=1.5)
    async def _run_rcon_commands(self, *args: RCONCommand) -> RCONResults:
        """
        *args = ("cmd1", "cmd2", "cmd3", ...)
        Каждый аргумент - отдельная команда, не ее часть
        Если аргумент - число, делается пауза (asyncio.sleep)
        """
        async with aiomcrcon.Client(
            self._rcon.host, self._rcon.port, self._rcon.password
        ) as client:
            logger.debug("RCON-подключение: {}", self._rcon)
            await client.connect()

            results = []
            for item in args:
                if isinstance(item, (int, float)):
                    logger.debug("RCON-пауза: {} сек", item)
                    await asyncio.sleep(item)
                    continue

                if len(item) > MAX_RCON_CMD_LEN:
                    raise MinecraftBotError(
                        f"Команда слишком длинная ({len(item)} из {MAX_RCON_CMD_LEN} симв.)"
                    )

                logger.debug("Выполнение RCON команды: {}", item)
                resp, id = await client.send_cmd(item)
                results.append(RCONResult(cmd=item, response=resp, req_id=id))

            return RCONResults(results)

    async def start_server(self, start_ok: bool = False) -> None:
        is_running = await self.is_service_running()
        if not is_running:
            result = await self._run_system_command(
                "sudo", "systemctl", "start", self._systemd_service
            )
            if not result.ok:
                raise ServerError(f"Ошибка запуска (> {result.cmd}): {result.stderr}")

            logger.info("Служба {} запущена", self._systemd_service)

        else:
            if start_ok:
                pass
            raise ServerError("Сервер уже запущен")

    async def stop_server(self, restart: bool = False) -> None:
        is_running = self.is_service_running()

        if is_running:
            await self._run_rcon_commands(
                f"say Сервер {'останавливается' if not restart else 'перезапускается'}...",
                3.5,
                "save-all",
                "stop",
                4,
            )

            result = await self._run_system_command(
                "sudo", "systemctl", "stop", self._systemd_service
            )
            if not result.ok:
                raise ServerError(f"Ошибка запуска {result.cmd}: {result.stderr}")

            logger.info("Cлужба {} остановлена", self._systemd_service)

        else:
            logger.info("Сервер уже остановлен. RCON-остановка не требуется")

    async def restart_server(self) -> None:
        await self.stop_server(restart=True)

        logger.info("Служба {} перезапущена", self._systemd_service)

        await self.start_server()

    async def is_service_running(self) -> bool:
        result = await self._run_system_command(
            "systemctl", "is-active", "--quiet", self._systemd_service
        )

        return result.ok

    async def get_detailed_status(self) -> ServerStatus:
        is_running = await self.is_service_running()
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

    @asynccontextmanager
    async def hold_world_saving(self):
        try:
            await self._run_rcon_commands("save-all flush", "save-off")
            yield

        finally:
            await self._run_rcon_commands("save-on")
