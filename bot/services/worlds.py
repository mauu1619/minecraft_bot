import shutil
from pathlib import Path

from bot.exceptions import (
    ActiveWorldError,
    MinecraftBotError,
    PropertiesNotFoundError,
    WorldAlreadyExistsError,
    WorldNotDeletedError,
    WorldNotFoundError,
)


class WorldsService:
    def __init__(self, server_dir: Path) -> None:
        self._srv_path = server_dir
        self._prop_path = server_dir / "server.properties"

    async def get_available_worlds(self) -> list[str]:
        worlds = []
        for item in self._srv_path.iterdir():
            if item.is_dir() and (item / "level.dat").exists():
                worlds.append(item.name)

        return sorted(worlds)

    async def get_current_world(self) -> str:
        if not self._prop_path.exists():
            raise PropertiesNotFoundError(
                "Файл 'server.properties' не найден на сервере"
            )

        try:
            with open(self._prop_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

                for line in lines:
                    if line.strip().startswith("level-name="):
                        return line.strip().split("=")[1]
        except Exception as exc:
            raise MinecraftBotError(
                f"Непредвиденная ошибка при чтении server.properties: {exc}"
            )

        raise MinecraftBotError("В server.properties отсуствует параметр 'level-name'")

    async def change_world_name(self, world_name: str) -> None:
        if not self._prop_path.exists():
            raise PropertiesNotFoundError(
                "Файл 'server.properties' не найден на сервере"
            )

        try:
            with open(self._prop_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as exc:
            raise MinecraftBotError(
                f"Непредвиденная ошибка при чтении server.properties: {exc}"
            )

        new_lines = []
        found_parameter = False

        for line in lines:
            if line.strip().startswith("level-name="):
                new_lines.append(f"level-name={world_name}\n")
                found_parameter = True
            else:
                new_lines.append(line)

        if not found_parameter:
            new_lines.append(f"\nlevel-name={world_name}\n")

        try:
            with open(self._prop_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as exc:
            raise MinecraftBotError(
                f"Непредвиденная ошибка при записи в server.properties: {exc}"
            )

    async def create_world(self, world_name: str) -> None:
        world_path = self._srv_path / world_name
        if world_path.exists():
            raise WorldAlreadyExistsError(
                f"✅ Мир с именем <code>{world_name}</code> уже существует!"
            )

        await self.change_world_name(world_name)

    async def delete_world(self, world_name: str) -> None:
        world_path = self._srv_path / world_name
        if not world_path.exists():
            raise WorldNotFoundError(f"Мир {world_name} не найден на диске")

        current_world = await self.get_current_world()
        if current_world == world_name:
            raise ActiveWorldError(
                "Нельзя удалить активный мир! Сначала переключитесь на другой"
            )

        try:
            shutil.rmtree(world_path)
        except (shutil.ExecError, NotImplementedError) as exc:
            raise WorldNotDeletedError(
                f"Системная ошибка при удалении мира: {exc}"
            ) from exc
