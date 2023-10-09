from aiogram import Router, types, Dispatcher, Bot
from token_api import TOKEN
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.types.bot_command import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

import json
import logging

import db
import api

import asyncio

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
rt = Router()
dp.include_router(rt)

""" READING CONFIG FILE """

with open('config.json', 'r') as f:
    config_json = json.load(f)
    BOT_TOKEN = config_json['BOT_TOKEN']
        # put wallets here to receive payments
    MAINNET_WALLET = config_json['MAINNET_WALLET']
    TESTNET_WALLET = config_json['TESTNET_WALLET']
    WORK_MODE = config_json['WORK_MODE']

if WORK_MODE == "mainnet":
    WALLET = MAINNET_WALLET
else:
        # By default, the bot will run on the testnet
    WALLET = TESTNET_WALLET

async def main() -> None:
    """Entry Point"""

    """Start Polling is the action of checking for new requests being sent to the bot from a user"""
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


""" STATES """
class DataInput (StatesGroup):
    firstState = State()
    secondState = State()
    WalletState = State()
    PayState = State()


""" HANDLERS """
@rt.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    await message.answer(f"WORKMODE: {WORK_MODE}")
    # Check if user is in database. if not, add him
    isOld = db.check_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    # if user already in database, we can address him differently
    if isOld == False:
        await message.answer(f"You are new here, {message.from_user.first_name}!")
        await message.answer(f"to buy air send /buy")
    else:
        await message.answer(f"Welcome once again, {message.from_user.first_name}!")
        await message.answer(f"to buy more air send /buy")
    await state.set_state(DataInput.firstState)

@rt.message(Command(BotCommand(command="cancel", description="cancel transaction")))
async def message_handler(message: Message, state: FSMContext) -> None:
    await message.answer("Canceled")
    await message.answer("/start to restart")
    state.set_state(DataInput.firstState)

@rt.message(Command(BotCommand(command="buy", description="But some air")))
@rt.message(DataInput.firstState)
async def cmd_buy(message: types.Message, state: FSMContext):
    # reply keyboard with air types
    buttons = []
    buttons.append(types.KeyboardButton(text='Just pure 🌫'))
    buttons.append(types.KeyboardButton(text='Spring forest 🌲'))
    buttons.append(types.KeyboardButton(text='Sea breeze 🌊'))
    buttons.append(types.KeyboardButton(text='Fresh asphalt 🛣'))
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, keyboard=[buttons])
    await message.answer(f"Choose your air: (or /cancel)", reply_markup=keyboard)
    await state.set_state(DataInput.secondState)

@rt.message(DataInput.secondState)
async def air_type(message: types.Message, state: FSMContext):
    print(message.text)
    if message.text == "Just pure 🌫":
        await state.update_data(air_type="Just pure 🌫")
    elif message.text == "Fresh asphalt 🛣":
        await state.update_data(air_type="Fresh asphalt 🛣")
    elif message.text == "Spring forest 🌲":
        await state.update_data(air_type="Spring forest 🌲")
    elif message.text == "Sea breeze 🌊":
        await state.update_data(air_type="Sea breeze 🌊")
    else:
        await message.answer("Wrong air type")
        await DataInput.secondState.set()
        return
    await state.set_state(DataInput.WalletState)
    await message.answer(f"Send your wallet address")

@rt.message(DataInput.WalletState)
async def user_wallet(message: types.Message, state: FSMContext):
    if len(message.text) == 48:
        res = api.detect_address(message.text)
        if res == False:
            await message.answer("Wrong wallet address")
            await state.set_state(DataInput.WalletState)
            return
        else:
            print("Wallet is Valid")
            user_data = await state.get_data()
            air_type = user_data['air_type']
            print("AirType: ", air_type)

            # inline button "check transaction"
            buttons2 = []
            buttons2.append(types.InlineKeyboardButton(text="Check transaction", callback_data="check"))
            keyboard2 = types.InlineKeyboardMarkup(inline_keyboard=[buttons2])

            
            buttons1 = []
            buttons1.append(types.InlineKeyboardButton(text="Ton Wallet", url=f"ton://transfer/{WALLET}?amount=1000000000&text={air_type}"))
            buttons1.append(types.InlineKeyboardButton(text="Tonkeeper", url=f"https://app.tonkeeper.com/transfer/{WALLET}?amount=1000000000&text={air_type}"))
            buttons1.append(types.InlineKeyboardButton(text="Tonhub", url=f"https://tonhub.com/transfer/{WALLET}?amount=1000000000&text={air_type}"))
            keyboard1 = types.InlineKeyboardMarkup(inline_keyboard=[buttons1])

            await message.answer(f"You choose {air_type}")
            await message.answer(f"Send <code>1</code> toncoin to address \n<code>{WALLET}</code> \nwith comment \n<code>{air_type}</code> \nfrom your wallet ({message.text})", reply_markup=keyboard1)
            await message.answer(f"Click the button after payment", reply_markup=keyboard2)
            await state.set_state(DataInput.PayState)
            await state.update_data(wallet=res)
            await state.update_data(value_nano="1000000000")
    else:
        await message.answer("Wrong wallet address")
        await state.set_state(DataInput.WalletState)

@rt.message(Command(BotCommand(command="me", description="Info bout me")))
async def cmd_me(message: types.Message):
    await message.answer(f"Your transactions")
    # db.get_user_payments returns list of transactions for user
    transactions = db.get_user_payments(message.from_user.id)
    if transactions == False:
        await message.answer(f"You have no transactions")
    else:
        for transaction in transactions:
            # we need to remember that blockchain stores value in nanotons. 1 toncoin = 1000000000 in blockchain
            await message.answer(f"{int(transaction['value'])/1000000000} - {transaction['comment']}")


@rt.callback_query(lambda call: call.data == "check")
@rt.message(DataInput.PayState)
async def check_transaction(call: types.CallbackQuery, state: FSMContext):
    # send notification
    user_data = await state.get_data()
    source = user_data['wallet']
    value = user_data['value_nano']
    comment = user_data['air_type']
    result = api.find_transaction(source, value, comment)
    if result == False:
        await call.answer("Wait a bit, try again in 10 seconds. You can also check the status of the transaction through the explorer (tonscan.org/)", show_alert=True)
    else:
        db.v_wallet(call.from_user.id, source)
        await call.message.edit_text("Transaction is confirmed \n/start to restart")
        await state.finish()
        await DataInput.firstState.set()

"""
1. What is MemoryStorage?
2. What is ParseMode HTML?
3. How do I use State checks in aiogram3?
4. How to do @dp.message_handler in aiogram3?
5. 

"""

if __name__ == "__main__":
    asyncio.run(main())