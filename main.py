import os

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

from app.bot.handlers import auth, location, profile, start
from app.services.session import TinderSessionManager


def create_dispatcher() -> Dispatcher:
    bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)

    sessions = TinderSessionManager()

    start.register(dp)
    auth.register(dp, sessions)
    profile.register(dp, sessions)
    location.register(dp, sessions)

    return dp


if __name__ == "__main__":
    executor.start_polling(create_dispatcher(), skip_updates=True)
