# --- Базовая Ошибка ---
class MinecraftBotError(Exception):
    pass


# --- Ошибки Миров ---
class WorldError(MinecraftBotError):
    pass


class WorldAlreadyExistsError(WorldError):
    pass


class WorldNotFoundError(WorldError):
    pass


class ActiveWorldError(WorldError):
    pass


class WorldNotDeletedError(WorldError):
    pass


# --- Ошибки Сервера ---
class ServerError(MinecraftBotError):
    pass


class PropertiesNotFoundError(ServerError):
    pass


class RconConnectionError(ServerError):
    pass
