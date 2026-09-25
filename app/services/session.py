from typing import Dict

from app.tinder.client import TinderClient


class TinderSessionManager:
    """Keeps one Tinder API client per Telegram user in memory."""

    def __init__(self):
        self._clients: Dict[int, TinderClient] = {}

    def get_client(self, telegram_user_id: int) -> TinderClient:
        if telegram_user_id not in self._clients:
            self._clients[telegram_user_id] = TinderClient()
        return self._clients[telegram_user_id]

    def remove(self, telegram_user_id: int) -> None:
        self._clients.pop(telegram_user_id, None)
