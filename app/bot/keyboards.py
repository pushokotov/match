from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("Авторизоваться по телефону", callback_data="auth:phone")],
            [InlineKeyboardButton("Ввести Tinder token (тест)", callback_data="auth:token")],
        ]
    )


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        "Мой профиль"
    ).add(
        "Запустить AutoSwipe"
    )
