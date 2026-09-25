from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.helper import Helper, HelperMode, ListItem
import phonenumbers
from phonenumbers import carrier
from phonenumbers.phonenumberutil import number_type
from api import BOT
import logging
import os

from requests import auth

from vars import *

api = BOT()
bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())
logging.basicConfig(level=logging.INFO)
user = types.user.User


class Form(StatesGroup):
    start = State()
    phone_number = State()
    auth_code = State()
    token_auth = State()
    user_logged_id = State()
    location = State()
    wait_for_new_location = State()
    run_autoliking = State()
    profiles_collected = State()


@dp.message_handler(commands=['start'])
@dp.message_handler(state="start")
async def cmd_start(message, state: FSMContext):
    await state.finish()
    text = f"Hi, {message.from_user.full_name} \nYou are welcome to the Match v0.6.1"
    inline_phone_auth_btn = InlineKeyboardButton("Sign in with phone number", callback_data='phone_number_auth')
    inline_token_auth_btn = InlineKeyboardButton("Sign in with token", callback_data='token_auth')
    # inline_fb_auth = InlineKeyboardButton("Войти через Facebook", callback_data="fb_auth")
    # inline_google_auth = InlineKeyboardButton("Войти через Google", callback_data="google_auth")
    inline_greet_kb = InlineKeyboardMarkup(row_width=1).add(inline_phone_auth_btn, inline_token_auth_btn)
    await bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=inline_greet_kb)


@dp.message_handler(Text(equals="Run AutoSwipe", ignore_case=True), state="*")
@dp.message_handler(commands="Run AutoSwipe", state="*")
async def set_user_location(message: types.Message, state: FSMContext):
    await Form.location.set()
    current_state = await state.get_state()
    logging.info(f"location funk Current state is {current_state}")
    enter_location_text = f"Enter city :"
    await message.reply(enter_location_text, reply=False)
    await Form.wait_for_new_location.set()


@dp.message_handler(state=Form.wait_for_new_location, content_types=types.ContentTypes.TEXT)
async def wait_for_new_location(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        current_state = await state.get_state()
        logging.info(f"wait_for_new_location  Current state is {current_state}")
        data['location'] = message.text
        location_list = [item for item in data['location'].split(', ')]
        logging.info(f"Your new location is {data['location']}")
        matches_count_before_start = await get_new_matches_count()
        for each in location_list:
            message_id = await run_bot(message, each)
            chat_id = message.chat.id
            print(chat_id, message_id)
            liked_amount = api.LIKE_RESULT.get(each)
            if liked_amount:
                updated_message_text_positive = f"{api.LIKE_RESULT.get(each)} were swiped in {each}:"
                await bot.edit_message_text(text=updated_message_text_positive, chat_id=chat_id,
                                            message_id=message_id)
            else:
                updated_message_text_negative = f"We haven't found any user in selected location. city \nPlease, try again."
                await bot.edit_message_text(text=updated_message_text_negative, chat_id=chat_id,
                                            message_id=message_id)
        matches_count_after_start = await get_new_matches_count()
        await bot.send_message(message.chat.id, f"AutoSwipe has beed finished. \nYou have {matches_count_after_start - matches_count_before_start} new matches.",
                               reply_markup=add_reply_keyboard(
                                   ["Profile information", "Run AutoSwipe",
                                    "Stop"]))
    await Form.user_logged_id.set()


async def run_bot(message, location):
    mess = await bot.send_message(message.chat.id, f"Swiping in {location}...")
    api.tg_run(location)
    return mess.message_id


async def get_new_matches_count():
    return api.tg_get_new_matches_count()


# You can use state '*' if you need to handle all states
@dp.message_handler(Text(equals='Stop', ignore_case=True), state="*")
@dp.message_handler(commands='Stop', state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    logging.info('cancel - Current state %r', current_state)
    if current_state is None:
        return
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Bot has been stoped', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(Text(equals='Try again', ignore_case=True), state="*")
@dp.message_handler(commands='Try again', state="*")
async def cancel_handler1(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    logging.info('Current state %r', current_state)
    if current_state is None:
        return

    # Cancel state and inform user about it
    await Form.previous()
    # And remove keyboard (just in case)
    text = "Please, try again"
    await message.reply(text, reply_markup=types.ReplyKeyboardRemove(), reply=False)
    current_state = await state.get_state()
    logging.info('Current state %r', current_state)


def verify_phone_number(number):
    n = phonenumbers.parse(number)
    return phonenumbers.is_valid_number(n)


@dp.message_handler(state=Form.phone_number)
async def post_phone_number_request(message: types.Message, state: FSMContext):
    if not verify_phone_number(message.text) is True:
        text = f"Ups. Enter correct phone number"
        await bot.send_message(message.chat.id, text)
        await Form.phone_number.set()
    else:
        await Form.phone_number.set()
        async with state.proxy() as data:
            data['phone_number'] = message.text
            text = f"Please enter the code sent to {data['phone_number']}. \n\nIf you haven't recieved it within 10 seconds, click on try again button"
            current_state = await state.get_state()
            logging.info('post_phone_number = Current state %r', current_state)
            r = api.tg_auth_enter_phone_number(data['phone_number'])
            if not r.status_code == 200:
                text = f"Ups. Enter correct phone number, please."
                await bot.send_message(message.chat.id, text)
                await Form.phone_number.set()
            else:
                await bot.send_message(message.chat.id, text, parse_mode='html',
                                       reply_markup=add_reply_keyboard(["Try again", "Stop"]))
                await Form.auth_code.set()


@dp.callback_query_handler(text='phone_number_auth')
async def call_back_for_phone_number_button(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id,
                           'Enter a phone number connected to your account, please.')
    await Form.phone_number.set()
    return True


@dp.callback_query_handler(text='change_location')
async def change_location_query_handler(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Enter new location: ")
    await Form.location.set()
    return True


@dp.callback_query_handler(text="token_auth")
async def call_back_for_token_auth(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Enter token: ")
    await Form.token_auth.set()
    return True


@dp.message_handler(state=Form.token_auth)
async def auth_with_token(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["token"] = message.text
        api.tg_auth_with_token(data["token"])
        await bot.send_message(message.chat.id, text="Authorization complete", reply_markup=add_reply_keyboard(
            ["Profile information", "Run AutoSwipe", "Stop"]))
        await Form.user_logged_id.set()


@dp.message_handler(state=Form.auth_code)
async def post_auth_code_request(message: types.Message, state: FSMContext):
    auth_code = message.text
    if not auth_code.isdigit() or len(auth_code) != 6:
        text = f"Ups. Please, enter valid code"
        await bot.send_message(message.chat.id, text)
        await Form.auth_code.set()
    else:
        async with state.proxy() as data:
            keyboard = add_reply_keyboard(["Try again", "Stop"])
            data['auth_code'] = message.text
            print(data['auth_code'], data['phone_number'])
            r = api.tg_post_auth_code(data['phone_number'], data['auth_code'])
            print(r, r.text)
            if r.status_code == 200:
                api.tg_generate_token(r)
                await bot.send_message(message.chat.id, get_user_info_message(),
                                       reply_markup=add_reply_keyboard(["Profile information", "Run AutoSwipe", "Stop"]))
                current_state = await state.get_state()
                logging.info('post_auth_code_request = Current state %r', current_state)
                await Form.user_logged_id.set()
            else:
                error_text = f"Ups. Try again.  \nEnter correct phone number: "
                await bot.send_message(message.chat.id, error_text, parse_mode='html', reply_markup=keyboard)
                await Form.phone_number.set()


@dp.message_handler(Text(equals="Profile information", ignore_case=True), state="*")
@dp.message_handler(commands="Profile information", state="*")
@dp.message_handler(state=Form.user_logged_id)
async def get_user_info(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    logging.info('get_user_info = Current state %r', current_state)
    return await bot_send_info_message(message, ["Switch location", "Profile information", "Run AutoSwipe", "Stop"])


def add_reply_keyboard(buttons):
    mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, row_width=1)
    for each in buttons:
        btn = KeyboardButton(each)
        mk.add(btn)
    return mk


async def bot_send_info_message(message: types.Message, reply_buttons):
    await bot.send_message(message.chat.id, get_user_info_message(), reply_markup=add_reply_keyboard(reply_buttons))


def get_user_info_message():
    information = api.tg_get_profile_info()
    city = information['city']
    return f"Hello, {information['user_name']}. \nYour current location is: {information['country']}, {city} \nNew users around: {api.tg_get_nearest_recs(city)} \nCommon number of matches: {api.tg_get_all_matches_count()} \nNumber of new matches: {api.tg_get_new_matches_count()}"


def get_user_information(information):
    info = api.tg_get_profile_info()
    return info[information]


def manage_swipe_limit():
    if api.PROFILE_PURCHASES is True:
        SWIPE_LIMIT = 10000


@dp.message_handler(commands='Try again', state="*")
@dp.message_handler(Text(equals='Try again', ignore_case=True), state="*")
async def cancel_handler1(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    logging.info('Current state %r', current_state)
    if current_state is None:
        return

    # Cancel state and inform user about it
    await Form.previous()
    # And remove keyboard (just in case)
    await message.reply('Enter a valid code, please.', reply_markup=types.ReplyKeyboardRemove())
    current_state = await state.get_state()
    logging.info('Current state %r', current_state)


async def shutdown(dispatcher: Dispatcher):
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False, on_shutdown=shutdown)
