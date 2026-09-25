from aiogram.dispatcher.filters.state import State, StatesGroup


class AuthStates(StatesGroup):
    waiting_phone = State()
    waiting_code = State()
    waiting_test_token = State()


class MainStates(StatesGroup):
    waiting_location = State()
    swiping = State()
