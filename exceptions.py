class APIError(Exception):
    """Ошибка API-сервиса."""

    pass


class StatusError(Exception):
    """Ошибка статуса домашней работы."""

    pass


class SendError(Exception):
    """Ошибка отправки сообщения."""

    pass
