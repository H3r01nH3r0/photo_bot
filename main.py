from aiogram import Bot, Dispatcher, types, filters, executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from utils import get_config, str2file
from database import DataBase
from nav import Keyboards
from asyncio import sleep
import asyncio
import time
import amplitude


commands = ['/start', '/clean', '/about', "/mail", "/mailing", '/export', "/users", "/count", "/help"]
config_filename = 'config.json'
config = get_config(config_filename)
db = DataBase(config['air_table_api'], config['base_id'], config['table_name'], config['db_file'])
keyboards = Keyboards(config['keyboards'])
bot = Bot(token=config['bot_token'], parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())
owners_filter = filters.IDFilter(user_id=config['owners'])


class Form(StatesGroup):
    mailing = State()
    mailing_markup = State()
    user_name = State()
    user_address = State()
    photos = State()
    picture = State()


async def process(users: list, kwargs: dict):
    total = 0
    sent = 0
    unsent = 0
    for user in users:
        kwargs['chat_id'] = user
        try:
            await bot.copy_message(**kwargs)
            sent += 1
        except Exception:
            unsent += 1
        await sleep(config["sleep_time"])
        total += 1
    return total, sent, unsent


async def sub_proc(users: list, kwargs: dict):
    number = len(users) // 5
    t = 0
    s = 0
    u = 0
    for total, sent, unsent in await asyncio.gather(
        process(users[:number], kwargs),
        process(users[number:2 * number], kwargs),
        process(users[2 * number:3 * number], kwargs),
        process(users[3 * number:4 * number], kwargs),
        process(users[4 * number:], kwargs)
    ):
        t += total
        s += sent
        u += unsent
    return t, s, u


@dp.message_handler(owners_filter, commands=["export"])
async def owners_export_command_handler(message: types.Message) -> None:
    msg = await message.answer(text=config["texts"]["please_wait"])
    file = str2file(" ".join([str(user[0]) for user in db.get_users()]), "users.txt")
    try:
        await message.answer_document(file)
    except:
        await message.answer(text=config["texts"]["no_users"])
    await msg.delete()


@dp.message_handler(owners_filter, commands=["users", "count"])
async def owners_users_command_handler(message: types.Message) -> None:
    count = db.get_users_count()
    await message.answer(text=config["texts"]["users_count"].format(count=count))


@dp.message_handler(owners_filter, commands=["mail", "mailing"])
async def owners_mailing_command_handler(message: types.Message) -> None:

    await Form.mailing.set()

    await message.answer(
        text=config["texts"]["enter_mailing"],
        reply_markup=keyboards.cancel()
    )


@dp.message_handler(content_types=types.ContentType.all(), state=Form.mailing)
async def owners_process_mailing_handler(message: types.Message, state: FSMContext) -> None:

    async with state.proxy() as data:
        data["message"] = message.to_python()

    await Form.mailing_markup.set()

    await message.answer(
        config["texts"]["enter_mailing_markup"],
        reply_markup=keyboards.cancel()
    )


@dp.message_handler(state=Form.mailing_markup)
async def owners_process_mailing_markup_handler(message: types.Message, state: FSMContext) -> None:

    try:
        if message.text not in ["-", "."]:
            try:
                markup = keyboards.from_str(message.text)
            except:
                await message.answer(
                    text=config["texts"]["incorrect_mailing_markup"],
                    reply_markup=keyboards.cancel()
                )
                return
        else:
            markup = types.InlineKeyboardMarkup()
        markup = markup.to_python()
        async with state.proxy() as data:
            _message = data["message"]

        await state.finish()
        await message.answer(config["texts"]["start_mailing"])
        started = time.time()
        kwargs = {
            "from_chat_id": _message["chat"]["id"],
            "message_id": _message["message_id"],
            "reply_markup": markup
        }
        user_list = [user[0] for user in db.get_users()]

        total, sent, unsent = await sub_proc(user_list, kwargs)

        await message.answer(
            config["texts"]["mailing_stats"].format(
                total=total,
                sent=sent,
                unsent=unsent,
                time=round(time.time() - started, 3)
            )
        )
    except Exception as a:
        print(a)


@dp.message_handler(commands=["clean"])
async def about_handler(message: types.Message):
    try:
        amplitude.statistics(message.from_user.id, message.text)
        await bot.send_message(
            message.from_user.id,
            text=config['texts']['cancel'],
            reply_markup=keyboards.cancel_all()
        )
    except Exception:
        pass


@dp.message_handler(commands=["help"])
async def about_handler(message: types.Message):
    try:
        amplitude.statistics(message.from_user.id, message.text)
        await bot.send_message(
            message.from_user.id,
            text=config['texts']['help'],
            reply_markup=keyboards.start_5()
        )
    except Exception:
        pass

@dp.message_handler(commands=["about"])
async def about_handler(message: types.Message):
    try:
        amplitude.statistics(message.from_user.id, message.text)
        await bot.send_message(
            message.from_user.id,
            text=config['texts']['about'].format(config["photo_price"], config["delivery_price"]),
            reply_markup=keyboards.start_4()
        )
    except Exception:
        pass


@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    try:
        args = message.text.split(" ")[1:]
        if len(args) >= 1:
            msg = "activated from: " + str(args)
            amplitude.statistics(message.from_user.id, msg)
        else:
            amplitude.statistics(message.from_user.id, message.text)
        if not db.check_user(message.from_user.id):
            db.add_user(message.from_user.id)
        await bot.send_sticker(
            message.from_user.id,
            sticker=config["sticker_id"]
        )
        await bot.send_message(
            message.from_user.id,
            text=config['texts']['hello_message'].format(config['bot_name']),
            reply_markup=keyboards.start_1()
        )
    except Exception:
        pass


@dp.pre_checkout_query_handler()
async def pre_checkout_query(pre_check_out_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_check_out_query.id, ok=True)


@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def process_payment(message: types.Message):
    try:
        if message.successful_payment.invoice_payload.startswith('order'):
            user_id = message.successful_payment.invoice_payload.split('_')[-1]
            user_order = db.get_user_order(user_id)
            photos = user_order[4].split(',')
            db.save_to_air_table(
                user_order[1],
                user_order[7],
                user_order[2],
                user_order[3],
                user_order[6],
                photos,
                user_order[5]
            )
            for owner in config['owners']:
                await bot.send_message(
                    owner,
                    text=config['texts']['user_payed'].format(user_order[7], user_order[1], user_order[6])
                )
            await bot.send_message(user_order[1], text=config['texts']['successful_payment'])
    except Exception:
        pass


@dp.callback_query_handler(state="*")
async def callback_query_handler(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        amplitude.statistics(callback_query.from_user.id, callback_query.data)
        if callback_query.data == 'start_1':
            if not db.check_user_order(callback_query.from_user.id):
                db.add_user_order(callback_query.from_user.id, callback_query.from_user.username)
            await Form.user_name.set()
            await bot.send_message(
                callback_query.from_user.id,
                text=config['texts']['insert_name']
            )

        elif callback_query.data == 'start_2':
            await Form.photos.set()
            async with state.proxy() as data:
                data['users_photos'] = []
            await bot.send_message(
                callback_query.from_user.id,
                text=config['texts']['send_photo'],
                reply_markup=keyboards.start_3()
            )

        elif callback_query.data == 'correct_name':
            user_name = db.get_user_name(callback_query.from_user.id)
            if db.get_user_address(callback_query.from_user.id):
                await bot.send_message(
                    callback_query.from_user.id,
                    text=config['texts']['insert_address'].format(user_name)
                )
            else:
                await bot.send_message(
                    callback_query.from_user.id,
                    text=config['texts']['insert_address'].format(user_name)
                )
            await Form.user_address.set()

        elif callback_query.data == 'incorrect_name':
            await Form.user_name.set()
            await bot.send_message(
                callback_query.from_user.id,
                text=config['texts']['insert_name']
            )

        elif callback_query.data == 'correct_address':
            await bot.send_message(
                callback_query.from_user.id,
                text=config['texts']['photo_info'],
                reply_markup=keyboards.start_2()
            )

        elif callback_query.data == 'incorrect_address':
            user_name = db.get_user_name(callback_query.from_user.id)
            await Form.user_address.set()
            await bot.send_message(
                callback_query.from_user.id,
                text=config['texts']['insert_address'].format(user_name)
            )
        elif callback_query.data == 'no_more':
            await bot.send_photo(
                callback_query.from_user.id,
                open('picture.jpg', 'rb')
            )
            await bot.send_message(
                callback_query.from_user.id,
                text=config['texts']['send_picture'],
                reply_markup=keyboards.main('need_picture')
            )
        elif callback_query.data == 'send_more':
            await Form.photos.set()
            users_photo = db.get_users_photos(callback_query.from_user.id)
            users_photo = users_photo.split(',')
            async with state.proxy() as data:
                data['users_photos'] = users_photo
            await bot.send_message(
                callback_query.from_user.id,
                text=config['texts']['send_more_photo'],
                reply_markup=keyboards.start_3()
            )
        elif callback_query.data == 'yes_add_picture':
            await Form.picture.set()
            await bot.send_message(
                callback_query.from_user.id,
                text=config['texts']['send_picture_text']
            )
        elif callback_query.data == 'no_picture':
            db.update_user_picture_text(callback_query.data, callback_query.from_user.id)
            info = db.get_user_order(callback_query.from_user.id)
            price = config['photo_price'] * len(info[4].split(","))
            order_price = price + config['delivery_price']
            db.add_user_price(callback_query.from_user.id, order_price)
            await bot.send_message(
                callback_query.from_user.id,
                text=config['texts']['check_order_no_pic'].format(
                    info[2],
                    info[3],
                    price,
                    str(len(info[4].split(","))),
                    config['delivery_price'],
                    order_price
                ),
                reply_markup=keyboards.main("check_your_order")
            )

        elif callback_query.data == 'yes_order_is_correct':
            await bot.send_message(
                callback_query.from_user.id,
                text=config['texts']['choose_card'],
                reply_markup=keyboards.main('choose_payment')
            )

        elif callback_query.data == 'russian_card':
            price = db.get_user_order(callback_query.from_user.id)[6]
            price *= 100
            value = str(price/100.0) + '0'
            payload = f"order_{callback_query.from_user.id}"
            await bot.send_invoice(
                callback_query.from_user.id,
                title=config['title'],
                description=config["description"],
                payload=payload,
                provider_token=config['yoo_money_token'],
                currency="RUB",
                start_parameter="test_payment",
                prices=[
                    {
                        "label": "Руб",
                        "amount": price
                    }
                ],
                need_phone_number=True,
                send_phone_number_to_provider=True,
                provider_data={
                    "receipt": {
                        "items": [
                            {
                                "description": "Открытка и доставка",
                                "quantity": "1.00",
                                "amount": {
                                    "value": value,
                                    "currency": "RUB"
                                },
                                "vat_code": 1
                            }
                        ]
                    }
                }
            )

        elif callback_query.data == 'international_card':
            await bot.send_message(
                callback_query.from_user.id,
                text=config['texts']['only_russian_card'],
                reply_markup=keyboards.only_ru_cards()
            )

        elif callback_query.data == 'no_order_is_incorrect':
            await bot.send_message(
                callback_query.from_user.id,
                text=config['texts']['del_order'],
                reply_markup=keyboards.cancel_order()
            )

        elif callback_query.data == 'cancel_order':
            await Form.user_name.set()
            await bot.send_message(
                callback_query.from_user.id,
                text=config['texts']['insert_name']
            )

        elif callback_query.data == 'cancel_all':
            db.del_order(callback_query.from_user.id)
            await bot.send_sticker(
                callback_query.from_user.id,
                sticker=config["sticker_id"]
            )
            await bot.send_message(
                callback_query.from_user.id,
                text=config['texts']['hello_message'],
                reply_markup=keyboards.start_1()
            )

    except Exception:
        pass


@dp.message_handler(content_types=['text'], state=Form.picture)
async def insert_picture_text(message: types.Message, state: FSMContext):
    try:
        amplitude.statistics(message.from_user.id, message.text)
        if message.text in commands or message.text.startswith('/start'):
            await state.finish()
            if message.text.startswith('/start'):
                if not db.check_user(message.from_user.id):
                    db.add_user(message.from_user.id)
                await bot.send_sticker(
                    message.from_user.id,
                    sticker=config["sticker_id"]
                )
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['hello_message'].format(config['bot_name']),
                    reply_markup=keyboards.start_1()
                )
            elif message.text == '/clean':
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['cancel'],
                    reply_markup=keyboards.cancel_all()
                )
            elif message.text == '/about':
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['about'].format(config["photo_price"], config["delivery_price"]),
                    reply_markup=keyboards.start_4()
                )
            elif message.text in ["/mail", "/mailing"]:
                await Form.mailing.set()

                await message.answer(
                    text=config["texts"]["enter_mailing"],
                    reply_markup=keyboards.cancel()
                )
            elif message.text == '/export':
                msg = await message.answer(text=config["texts"]["please_wait"])
                file = str2file(" ".join([str(user[0]) for user in db.get_users()]), "users.txt")
                try:
                    await message.answer_document(file)
                except:
                    await message.answer(text=config["texts"]["no_users"])
                await msg.delete()
            elif message.text in ["/users", "/count"]:
                count = db.get_users_count()
                await message.answer(text=config["texts"]["users_count"].format(count=count))
            elif message.text == '/help':
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['help'],
                    reply_markup=keyboards.start_5()
                )
        else:
            db.update_user_picture_text(message.text, message.from_user.id)
            info = db.get_user_order(message.from_user.id)
            price = config['photo_price'] * len(info[4].split(","))
            order_price = price + config['delivery_price'] + config['picture_price']
            db.add_user_price(message.from_user.id, order_price)
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['check_order'].format(
                    info[2],
                    info[3],
                    price,
                    str(len(info[4].split(","))),
                    config['picture_price'],
                    '1',
                    info[5],
                    config['delivery_price'],
                    order_price
                ),
                reply_markup=keyboards.main("check_your_order")
            )
            await state.finish()
    except Exception:
        pass


@dp.message_handler(content_types=['text', 'photo'],  state=Form.photos)
async def get_photo(message: types.Message, state: FSMContext):
    try:
        if message.photo:
            file_id = message.photo[-1].file_id
            file_info = await bot.get_file(file_id)
            async with state.proxy() as data:
                data['users_photos'].append(file_info.file_path)
            if len(data["users_photos"]) <= 1:
                await bot.send_message(message.from_user.id, text=config['texts']['get_photo'])
            else:
                pass
        if message.text in ['Готово, я отправил все фото', "Готово", "готово", "ГОТОВО"]:
            async with state.proxy() as data:
                users_photos = data['users_photos']
            await state.finish()
            if users_photos:
                photos = ','.join(users_photos)
                db.update_users_photos(message.from_user.id, photos)
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['got_photo'].format(str(len(users_photos))),
                    reply_markup=keyboards.main('send_more_photos')
                )
            else:
                await state.finish()
                await Form.photos.set()
                async with state.proxy() as data:
                    data['users_photos'] = []
                await bot.send_message(message.from_user.id, text=config['texts']['no_photo_sent'])
        elif message.text in commands or message.text.startswith('/start'):
            await state.finish()
            if message.text.startswith('/start'):
                if not db.check_user(message.from_user.id):
                    db.add_user(message.from_user.id)
                await bot.send_sticker(
                    message.from_user.id,
                    sticker=config["sticker_id"]
                )
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['hello_message'].format(config['bot_name']),
                    reply_markup=keyboards.start_1()
                )
            elif message.text == '/clean':
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['cancel'],
                    reply_markup=keyboards.cancel_all()
                )
            elif message.text == '/about':
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['about'].format(config["photo_price"], config["delivery_price"]),
                    reply_markup=keyboards.start_4()
                )
            elif message.text in ["/mail", "/mailing"]:
                await Form.mailing.set()

                await message.answer(
                    text=config["texts"]["enter_mailing"],
                    reply_markup=keyboards.cancel()
                )
            elif message.text == '/export':
                msg = await message.answer(text=config["texts"]["please_wait"])
                file = str2file(" ".join([str(user[0]) for user in db.get_users()]), "users.txt")
                try:
                    await message.answer_document(file)
                except:
                    await message.answer(text=config["texts"]["no_users"])
                await msg.delete()
            elif message.text in ["/users", "/count"]:
                count = db.get_users_count()
                await message.answer(text=config["texts"]["users_count"].format(count=count))
            elif message.text == '/help':
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['help'],
                    reply_markup=keyboards.start_5()
                )

    except Exception:
        pass


@dp.message_handler(content_types=['text'], state=Form.user_name)
async def insert_user_name(message: types.Message, state: FSMContext):
    try:
        amplitude.statistics(message.from_user.id, message.text)
        if message.text in commands or message.text.startswith('/start'):
            await state.finish()
            if message.text.startswith('/start'):
                if not db.check_user(message.from_user.id):
                    db.add_user(message.from_user.id)
                await bot.send_sticker(
                    message.from_user.id,
                    sticker=config["sticker_id"]
                )
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['hello_message'].format(config['bot_name']),
                    reply_markup=keyboards.start_1()
                )
            elif message.text == '/clean':
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['cancel'],
                    reply_markup=keyboards.cancel_all()
                )
            elif message.text == '/about':
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['about'].format(config["photo_price"], config["delivery_price"]),
                    reply_markup=keyboards.start_4()
                )
            elif message.text in ["/mail", "/mailing"]:
                await Form.mailing.set()

                await message.answer(
                    text=config["texts"]["enter_mailing"],
                    reply_markup=keyboards.cancel()
                )
            elif message.text == '/export':
                msg = await message.answer(text=config["texts"]["please_wait"])
                file = str2file(" ".join([str(user[0]) for user in db.get_users()]), "users.txt")
                try:
                    await message.answer_document(file)
                except:
                    await message.answer(text=config["texts"]["no_users"])
                await msg.delete()
            elif message.text in ["/users", "/count"]:
                count = db.get_users_count()
                await message.answer(text=config["texts"]["users_count"].format(count=count))
            elif message.text == '/help':
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['help'],
                    reply_markup=keyboards.start_5()
                )
        else:
            db.update_user_name(message.text, message.from_user.id)
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['check_name'].format(message.text),
                reply_markup=keyboards.main("is_name_correct")
            )
            await state.finish()
    except Exception:
        pass


@dp.message_handler(content_types=['text'], state=Form.user_address)
async def insert_user_address(message: types.Message, state: FSMContext):
    try:
        amplitude.statistics(message.from_user.id, message.text)
        if message.text in commands or message.text.startswith('/start'):
            await state.finish()
            if message.text.startswith('/start'):
                if not db.check_user(message.from_user.id):
                    db.add_user(message.from_user.id)
                await bot.send_sticker(
                    message.from_user.id,
                    sticker=config["sticker_id"]
                )
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['hello_message'].format(config['bot_name']),
                    reply_markup=keyboards.start_1()
                )
            elif message.text == '/clean':
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['cancel'],
                    reply_markup=keyboards.cancel_all()
                )
            elif message.text == '/about':
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['about'].format(config["photo_price"], config["delivery_price"]),
                    reply_markup=keyboards.start_4()
                )
            elif message.text in ["/mail", "/mailing"]:
                await Form.mailing.set()

                await message.answer(
                    text=config["texts"]["enter_mailing"],
                    reply_markup=keyboards.cancel()
                )
            elif message.text == '/export':
                msg = await message.answer(text=config["texts"]["please_wait"])
                file = str2file(" ".join([str(user[0]) for user in db.get_users()]), "users.txt")
                try:
                    await message.answer_document(file)
                except:
                    await message.answer(text=config["texts"]["no_users"])
                await msg.delete()
            elif message.text in ["/users", "/count"]:
                count = db.get_users_count()
                await message.answer(text=config["texts"]["users_count"].format(count=count))
            elif message.text == '/help':
                await bot.send_message(
                    message.from_user.id,
                    text=config['texts']['help'],
                    reply_markup=keyboards.start_5()
                )
        else:
            db.update_user_address(message.text, message.from_user.id)
            await bot.send_message(
                message.from_user.id,
                text=config['texts']['check_address'].format(message.text),
                reply_markup=keyboards.main("is_address_correct")
            )
            await state.finish()
    except Exception:
        pass


if __name__ == "__main__":
    executor.start_polling(dispatcher=dp, skip_updates=False)
