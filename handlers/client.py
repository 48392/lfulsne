import asyncio
import datetime
from random import uniform, randint
import json

from aiogram import F, Router, types, Bot
from aiogram.filters.command import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import VERIF_CHANNEL_ID
from database.db import DataBase
from keyboards.client import ClientKeyboard
from other.filters import ChatJoinFilter, RegisteredFilter
from other.languages import languages

router = Router()


class RegisterState(StatesGroup):
    input_id = State()


class GetSignalStates(StatesGroup):
    chosing_mines = State()


class ChangeReferral(StatesGroup):
    input_ref = State()


# Тексты сообщений и кнопки (по скриншотам)
POSTBACK_CHAIN = [
    {
        "text": "Поздравляем с успешной регистрацией! 🥳\n\nШаг 2 - Внеси первый депозит.\n\n✦ Чем больше депозит, тем больше УРОВЕНЬ в боте, а чем больше уровень в боте, тем больше количество сигналов с высокой вероятностью проходимости сигнала ты будешь получать.\n\n• После пополнения первого депозита, Вам автоматически придет <b>уведомление</b> в бота.",
        "button": "Внести депозит"
    },
    {
        "text": "Главное меню:\n",
        "webapp": "first.html",
        "event_next": "bonus_claimed"
    },
    {
        "text": "ЗАБИРАЙ СВОИ БОНУСЫ ПРЯМО СЕЙЧАС\n\nПо мимо того что ты выиграл +70 Фриспинов на более чем 10 различных слотов, мы ДАРИМ тебе еще 1 акцию в виде раздачи криптовалюты!",
        "webapp": "cryptobot.html",
        "webapp_button_text": "🎁 Забрать крипто-бонуску",
        "event_next": "crypto_bonus_claimed",
        "button2": "Забрать 70 FP"
    },
    {
        "text": "ЧЕК КРИПТОБОТ\n\nВыиграть мега бонуску!",
        "webapp": "second.html",
        "event_next": "megabonus_claimed"
    },
    {
        "text": "ОГО! ТЕПЕРЬ В РУЛЕТКЕ МОЖНО ВЫИГРАТЬ СРАЗУ 2 ПОЗИЦИИ!!!\n\nПолучи БЕСПРОИГРЫШНЫЙ ШАНС X2 и выиграй: +220% К ДЕПОЗИТУ, БОНУСКА ЗА 32,000Р, ВАУЧЕР НА 10,000Р и многое другое!\n\nСхватить удачу за хвост!",
        "button": "Получить ШАНС X2"
    },
    {
        "text": "ТВОЙ ЧАС!\n\nХОЧЕШЬ СОРВАТЬ КУШ? ШАНС X2 ИСПОЛНИТ ТВОЁ ЖЕЛАНИЕ!\n\nДля этого просто сделай депозит на 1win от 2000Р, ты ничего не теряешь, ведь деньги остаются на твоём 1win аккаунте и ты всегда можешь их вывести 😉.\n\nБеспроигрышный шанс уже сейчас!",
        "button": "Сделать депозит от 2000Р"
    },
    {
        "text": "ЕЕЕ БОЙ!\n\nТЫ В ШАГЕ ОТ НАСТОЯЩЕЙ БУРИ ЗАНОСОВ!\n\nШанс X2 уже у тебя в руках, просто крути рулетку и гарантированно ЗАБИРАЙ СРАЗУ 2 ПОЗИЦИИ!",
        "button": "Забрать ШАНС X2",
        "webapp": "x2.html",
        "event_next": "x2_claimed"
    },
    {
        "text": "А ТЕПЕРЬ САМОЕ ИНТЕРЕСНОЕ!\n\nПрямо сейчас ты забираешь КОМБО. Объясню! Ты выиграл +220% к депозиту и ШАНС x3 для которого нужно сделать депозит от 3,500Р\n\nПоэтому ты сразу УБИВАЕШЬ ДВУХ ЗАЙЦЕВ, делаешь депозит, который остаётся у тебя на балансе + получаешь 220% + ШАНС X3! Не шикарно ли?",
        "button": "Сделать депозит от 3500Р"
    },
    {
        "text": "О БОЖЕ МОЙ, ЧТО ТЕБЯ СЕЙЧАС ЖДЁТ!\n\nПрямо сейчас, просто в 1 клик, ты забираешь все позиции используя ШАНС X3, до этого дойдут единицы! Но только единицам, достаются все сливки 😉\n\nЗабрать своё",
        "button": "Забрать своё",
        "webapp": "x3.html",
        "event_next": "x3_claimed"
    },
    {
        "text": "С ЭТОЙ БОНУСКОЙ ТЕБЯ ЖДЕТ МЕГА ЗАНОС!",
        "button": "Получить мега занос"
    },
    {
        "text": "НУ ВОТ И ВСЕ ТЫ НА ФИНИШНОЙ ПРЯМОЙ!",
        "button": "Забрать финальный приз",
        "webapp": "last.html",
        "event_next": "final_prize_claimed"
    }
]

# Состояния для FSM
class PostbackChainStates(StatesGroup):
    step = State()

# Клавиатура для шага
async def get_chain_keyboard(step_idx: int):
    ikb = InlineKeyboardBuilder()
    current_step_data = POSTBACK_CHAIN[step_idx]
    next_step_data_cb = f"postback_chain|{step_idx+1}"

    # Добавляем кнопку webapp, если она есть
    if 'webapp' in current_step_data:
        # Для первой миниаппы используем first.html, для остальных — как раньше
        if current_step_data['webapp'] == 'first.html':
            cache_buster = f"?v={datetime.datetime.now().timestamp()}"
            webapp_url = f"https://48392.github.io/lfulsne/first.html{cache_buster}"
        else:
            cache_buster = f"?v={datetime.datetime.now().timestamp()}"
            webapp_url = f"https://48392.github.io/lfulsne/{current_step_data['webapp']}{cache_buster}"
        button_text = current_step_data.get('webapp_button_text', "🎮 Открыть игру")
        ikb.button(text=button_text, web_app=types.WebAppInfo(url=webapp_url))

    # Добавляем обычную кнопку, если она есть
    if 'button' in current_step_data:
        ikb.button(text=current_step_data['button'], callback_data=next_step_data_cb)

    # Добавляем вторую кнопку, если она есть
    if 'button2' in current_step_data:
        # Предполагаем, что вторая кнопка всегда является ссылкой
        ikb.button(text=current_step_data['button2'], url="https://telegra.ph")

    return ikb.as_markup()

# Запуск цепочки после постбека (после успешной верификации)
async def start_postback_chain(user_id: int, bot: Bot):
    step_idx = 0
    await DataBase.update_current_step(user_id, step_idx)
    await bot.send_message(
        chat_id=user_id,
        text=POSTBACK_CHAIN[step_idx]['text'],
        reply_markup=await get_chain_keyboard(step_idx),
        parse_mode="HTML"
    )

# Обработчик для кнопок цепочки
@router.callback_query(F.data.startswith("postback_chain|"))
async def postback_chain_callback(callback: types.CallbackQuery, bot: Bot):
    step_idx = int(callback.data.split("|")[1])
    user_id = callback.from_user.id
    
    await DataBase.update_current_step(user_id, step_idx)
    await callback.message.delete()
    
    if step_idx < len(POSTBACK_CHAIN):
        await bot.send_message(
            chat_id=user_id,
            text=POSTBACK_CHAIN[step_idx]['text'],
            reply_markup=await get_chain_keyboard(step_idx),
            parse_mode="HTML"
        )


@router.message(CommandStart())
async def start_command(message: types.Message, user_id: int = 0):
    await message.delete()
    user = await DataBase.get_user_info(message.from_user.id if user_id == 0 else user_id)
    if user is None:
        await get_language(message, True)
        return

    await message.answer(languages[user[2]]["welcome"].format(first_name=message.from_user.first_name),
                         reply_markup=await ClientKeyboard.start_keyboard(user[2]), parse_mode="HTML")


@router.callback_query(F.data.startswith("sel_lang"))
async def select_language(callback: CallbackQuery):
    data = callback.data.split("|")
    
    # Проверяем формат данных
    if len(data) >= 3 and data[1].isdigit():
        # Старый формат: sel_lang|user_id|lang
        await DataBase.register(callback.from_user.id, data[2])
        await start_command(message=callback.message, user_id=int(data[1]))
    else:
        # Новый формат из цепочки: sel_lang|postback_chain|step|lang
        # Этот случай обрабатывается в select_language_in_chain
        await callback.answer("Выбор языка обрабатывается...")


@router.callback_query(F.data.startswith("resel_lang"))
async def reselect_language(callback: CallbackQuery):
    data = callback.data.split("|")
    
    # Проверяем формат данных
    if len(data) >= 3 and data[1].isdigit():
        # Формат: resel_lang|user_id|lang
        await DataBase.update_lang(int(data[1]), data[2])
        await start_command(message=callback.message, user_id=int(data[1]))
    else:
        await callback.answer("Ошибка формата данных")


@router.callback_query(F.data == "get_lang")
async def get_language(query: Message | CallbackQuery, first: bool = False):
    q = query
    if isinstance(query, CallbackQuery):
        query = query.message
    try:
        await query.delete()
    except:
        pass

    if first:
        prefix = f"sel_lang|{query.from_user.id}"
    else:
        prefix = f"resel_lang|{q.from_user.id}"
    await query.answer("Select language",
                       reply_markup=await ClientKeyboard.languages_board(prefix))


@router.callback_query(F.data == "check", ChatJoinFilter())
async def check_subscription_and_start_chain(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except:
        pass
    # Запуск цепочки постов сразу после проверки подписки
    await start_postback_chain(callback.from_user.id, callback.bot)
    await callback.answer()


@router.callback_query(F.data == "register")
async def register_handler(callback: types.CallbackQuery, state: FSMContext):
    lang = await DataBase.get_lang(callback.from_user.id)
    if lang is None:
        lang = "ru"  # По умолчанию русский
    text = languages[lang]["register_info"]


    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer(text, parse_mode="HTML",
                                  reply_markup=await ClientKeyboard.register_keyboard(callback, lang))
    await state.set_state(RegisterState.input_id)



@router.callback_query(F.data == "instruction")
async def instruction_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    new_ref_url = f"{(await DataBase.get_ref())}&sub1={user_id}"
    lang = await DataBase.get_lang(callback.from_user.id)
    if lang is None:
        lang = "ru"  # По умолчанию русский
    text = languages[lang]["instruction_info"].format(ref_url=new_ref_url)

    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer(text, reply_markup=await ClientKeyboard.back_keyboard(lang),
                                  parse_mode="HTML")



@router.message(F.chat.func(lambda chat: chat.id == int(VERIF_CHANNEL_ID)))
async def channel_verification_handler(message: types.Message):
    if (await DataBase.get_user(message.text)) is None:
        lang = await DataBase.get_lang(int(message.text))
        if lang is None:
            lang = "ru"  # По умолчанию русский
        await DataBase.update_verifed(message.text)
        await message.bot.send_message(chat_id=int(message.text),
                                       text=languages[lang]["success_registration"],
                                       reply_markup=await ClientKeyboard.get_signal_keyboard(lang), parse_mode="HTML")
        await start_postback_chain(int(message.text), message.bot)


@router.callback_query(F.data == "change_ref")
async def change_referral_callback_handler(callback: types.CallbackQuery, state: FSMContext):
    lang = await DataBase.get_lang(callback.from_user.id)
    if lang is None:
        lang = "ru"  # По умолчанию русский
    await callback.message.delete()
    await callback.message.answer(languages[lang]["enter_new_ref"])
    await state.set_state(ChangeReferral.input_ref)


@router.message(ChangeReferral.input_ref)
async def change_referral_message_state(message: types.Message, state: FSMContext):
    lang = await DataBase.get_lang(message.from_user.id)
    if lang is None:
        lang = "ru"  # По умолчанию русский
    await message.answer(languages[lang]["ref_changed"])
    await DataBase.edit_ref(message.text)
    await state.clear()


@router.message(F.web_app_data)
async def webapp_data_handler(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    print(f"\n[DEBUG] Получены данные от WebApp от пользователя {user_id}:")
    print(f"[DEBUG] RAW DATA: {message.web_app_data.data}")

    try:
        data = json.loads(message.web_app_data.data)
        event = data.get('event')
        print(f"[DEBUG] Событие: {event}")
    except (json.JSONDecodeError, AttributeError):
        print("[DEBUG] Ошибка: не удалось разобрать JSON или получить событие.")
        return

    user = await DataBase.get_user_info(user_id)
    if not user or user[4] is None:
        print("[DEBUG] Ошибка: не найден пользователь или его текущий шаг в БД.")
        return

    current_step_idx = user[4]
    print(f"[DEBUG] Текущий шаг пользователя: {current_step_idx}")

    expected_event = POSTBACK_CHAIN[current_step_idx].get('event_next')
    print(f"[DEBUG] Ожидаемое событие для этого шага: {expected_event}")

    if event and event == expected_event:
        print("[DEBUG] УСПЕХ: Событие совпало с ожидаемым. Перевожу на следующий шаг.")
        next_step_idx = current_step_idx + 1
        await DataBase.update_current_step(user_id, next_step_idx)

        if next_step_idx < len(POSTBACK_CHAIN):
            print(f"[DEBUG] Отправляю сообщение для шага {next_step_idx}.")
            await bot.send_message(
                chat_id=user_id,
                text=POSTBACK_CHAIN[next_step_idx]['text'],
                reply_markup=await get_chain_keyboard(next_step_idx),
                parse_mode="HTML"
            )
    else:
        print("[DEBUG] ПРЕДУПРЕЖДЕНИЕ: Полученное событие не совпало с ожидаемым. Ничего не делаю.")
