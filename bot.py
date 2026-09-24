"""
Telegram-бот @MariyaFedoseevaHelp_bot
Помощник визажиста Марии Федосеевой

Возможности:
- Приветствие и выявление потребности клиента
- Запись на услугу через пошаговый диалог
- Информация об обучении макияжу
- Просмотр услуг и цен
- Обратная связь (отзывы)
- Уведомления администратору о новых записях

Стек: aiogram 3 + Python 3.11+
Хостинг: Render.com (бесплатно)
"""

import os
import asyncio
import logging
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import aiohttp
from aiohttp import web

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from async_uds_api import UDSClient
from aiogram.filters import Command, StateFilter
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, Contact, FSInputFile,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode

# =========================
# Конфигурация
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")  # от @BotFather
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))  # ID Маши в Telegram
NOTIFY_TOPIC = os.getenv("NOTIFY_TOPIC", "mariya-booking-default")  # ntfy.sh топик для push


async def notify_push(title: str, body: str, priority: str = "high"):
    """Push в телефон через ntfy.sh — работает даже если Telegram закрыт"""
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(
                f"https://ntfy.sh/{NOTIFY_TOPIC}",
                data=body.encode("utf-8"),
                headers={
                    "Title": str(title),
                    "Priority": str(priority),
                    "Tags": "bell,scissors",
                },
                timeout=aiohttp.ClientTimeout(total=10),
            )
    except Exception as e:
        logger.error(f"ntfy.sh push error: {type(e).__name__}: {e}")
STUDIO_ADDRESS = "г. Сызрань, ул. Константина Федина, 33, 1 этаж, кабинет 111"
STUDIO_PHONE = "+7 (927) 896-46-64"
INSTAGRAM = "@marri_fedoseeva"
MAPS_URL = "https://yandex.ru/profile/114267583699"

# Услуги студии с ценами (из прайса Марии)
SERVICES = {
    "makeup_day": {
        "name": "Дневной макияж",
        "price": "3 000 ₽",
        "category": "Макияж",
    },
    "makeup_evening": {
        "name": "Вечерний макияж (пучки включены)",
        "price": "3 000 ₽",
        "category": "Макияж",
    },
    "makeup_graphic": {
        "name": "Графичный макияж / с элементами декора",
        "price": "3 500 ₽",
        "category": "Макияж",
    },
    "makeup_bride": {
        "name": "Свадебный макияж",
        "price": "4 000 ₽",
        "category": "Макияж",
    },
    "makeup_bride_trial": {
        "name": "Пробный свадебный макияж",
        "price": "3 000 ₽",
        "category": "Макияж",
    },
    "full_bridal": {
        "name": "Полный свадебный образ (макияж + причёска + проба)",
        "price": "15 000 ₽",
        "category": "Комплексные пакеты",
    },
    "express": {
        "name": "Экспресс-образ для фотосессии (макияж + укладка, 40-60 мин)",
        "price": "2 800–3 500 ₽",
        "category": "Комплексные пакеты",
    },
    "full_look": {
        "name": "Полный образ (макияж + укладка)",
        "price": "от 5 500 ₽",
        "category": "Комплексные пакеты",
    },
    "styling_short": {
        "name": "Укладка на короткие волосы",
        "price": "2 000 ₽",
        "category": "Укладки / причёски",
    },
    "styling_mid": {
        "name": "Укладка на средние (до лопаток)",
        "price": "2 500 ₽",
        "category": "Укладки / причёски",
    },
    "styling_long": {
        "name": "Укладка на длинные (ниже поясницы)",
        "price": "3 000–4 000 ₽",
        "category": "Укладки / причёски",
    },
    "styling_collected": {
        "name": "Собранная причёска",
        "price": "3 000–3 500 ₽",
        "category": "Укладки / причёски",
    },
    "styling_bride": {
        "name": "Свадебная / пробная причёска",
        "price": "4 000 ₽",
        "category": "Укладки / причёски",
    },
    "lamination_brows": {
        "name": "Ламинирование бровей",
        "price": "1 800 ₽",
        "category": "Брови / ресницы",
    },
    "lamination_lashes": {
        "name": "Ламинирование ресниц",
        "price": "1 800 ₽",
        "category": "Брови / ресницы",
    },
    "brows_correction": {
        "name": "Коррекция бровей пинцетом",
        "price": "700 ₽",
        "category": "Брови / ресницы",
    },
    "brows_tint": {
        "name": "Окрашивание + коррекция бровей",
        "price": "1 000 ₽",
        "category": "Брови / ресницы",
    },
    "shugaring_face": {
        "name": "Шугаринг лица / зоны",
        "price": "от 300 ₽",
        "category": "Шугаринг",
    },
    "shugaring_armpits": {
        "name": "Шугаринг подмышек",
        "price": "500 ₽",
        "category": "Шугаринг",
    },
    "shugaring_bikini": {
        "name": "Шугаринг бикини",
        "price": "700–1 300 ₽",
        "category": "Шугаринг",
    },
    "shugaring_shins": {
        "name": "Шугаринг голеней",
        "price": "1 000 ₽",
        "category": "Шугаринг",
    },
    "shugaring_thighs": {
        "name": "Шугаринг бёдер",
        "price": "700 ₽",
        "category": "Шугаринг",
    },
    "shugaring_legs_full": {
        "name": "Шугаринг ног полностью",
        "price": "1 500 ₽",
        "category": "Шугаринг",
    },
    "kids_styling": {
        "name": "Детская укладка",
        "price": "1 500 ₽",
        "category": "Детям",
    },
    "extra_home_visit": {
        "name": "Выезд на дом по городу",
        "price": "1 000–2 000 ₽",
        "category": "Дополнительные услуги",
    },
    "extra_early_visit": {
        "name": "Ранний выезд (06:00–08:00)",
        "price": "1 000 ₽",
        "category": "Дополнительные услуги",
    },
    "extra_before_6am": {
        "name": "Выезд ранее 06:00",
        "price": "+500 ₽ за каждый час",
        "category": "Дополнительные услуги",
    },
}

# Курсы обучения
COURSES = {
    "self": {
        "name": "Курс «Сам себе визажист»",
        "price": "8 000 ₽",
        "desc": "Научитесь делать стойкий макияж за 30 минут каждое утро. Экономия на визажисте — от 15 000 ₽/мес.",
        "category": "Очное обучение",
    },
    "online_5": {
        "name": "5 онлайн-уроков (пакетом)",
        "price": "1 800 ₽ (пакет, экономия 200₽)",
        "desc": "«Растушёванная стрелка», «Нежный коричневый смоки», «Смоки-айс», «Вечерний макияж», «Макияж из 4 средств».",
        "category": "Онлайн-обучение",
    },
    "master_class_adult": {
        "name": "Мастер-класс взрослый",
        "price": "1 500 ₽",
        "desc": "Индивидуальный или групповой мастер-класс по любой технике макияжа.",
        "category": "Очное обучение",
    },
    "master_class_kid": {
        "name": "Мастер-класс детский",
        "price": "1 000 ₽",
        "desc": "Мастер-класс по макияжу для девочек 8-14 лет — подарить ребёнку радость.",
        "category": "Очное обучение",
    },
}

# Время работы
WORK_HOURS = {
    "ПН": "9:00–20:00",
    "ВТ": "9:00–20:00",
    "СР": "9:00–20:00",
    "ЧТ": "9:00–20:00",
    "ПТ": "9:00–20:00",
    "СБ": "10:00–18:00",
    "ВС": "по договорённости",
}

# Ссылки для регистрации клиентов в UDS-программе лояльности
UDS_REGISTER_LINKS = {
    "app": "https://fedoseeva.uds.app/c/join?ref=cvpv5571",
    "tg": "https://t.me/Fedoseevamakeup_bot?start=cvpv5571",
    "max": "https://max.ru/id632512231585_bot?start=cvpv5571",
}
UDS_REF = "cvpv5571"

# Доступные временные слоты
TIME_SLOTS = [
    "9:00", "10:00", "11:00", "12:00", "13:00",
    "14:00", "15:00", "16:00", "17:00", "18:00", "19:00",
]

# =========================
# Инициализация
# =========================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

router = Router()
dp.include_router(router)

# =========================
# Специальные обработчики для пересланных сообщений
# =========================

@router.message(F.forward_from_chat)
async def log_forwarded_channel(message: Message):
    """Получили пересланный пост из канала — больше не используется"""
    pass

@router.message(F.forward_from)
async def log_forwarded_user(message: Message):
    """Получили пересланный пост от пользователя — больше не используется"""
    pass


# Трекеры для followup сообщений: user_id -> True, если человек только что увидел описание курса
state_self_waiter: dict[int, bool] = {}
state_master_waiter: dict[int, bool] = {}

# =========================
# Followup: если человек не нажал «Записаться» в курсах — предложить онлайн-уроки
# =========================

async def self_course_followup(user_id: int, chat_id: int, original_msg_id: int):
    """Через 90 сек, если пользователь не перешёл — предложить онлайн-уроки"""
    await asyncio.sleep(90)
    if state_self_waiter.get(user_id):
        try:
            text = (
                "💡 <b>Пока думаешь — может, попробовать сначала онлайн?</b>\n\n"
                "5 коротких видеоуроков — от 199 ₽:\n"
                "• Растушёванная стрелка (499 ₽)\n"
                "• Нежный коричневый смоки (499 ₽)\n"
                "• Смоки-айс (399 ₽)\n"
                "• Вечерний макияж (399 ₽)\n"
                "• Макияж из 4 средств (199 ₽)\n\n"
                "📦 Пакетом — <b>1 800 ₽</b> (экономия 200 ₽).\n\n"
                "👇 Нажми, чтобы посмотреть подробности:"
            )
            buttons = [
                [InlineKeyboardButton(text="🎬 Посмотреть онлайн-уроки", callback_data="online_lessons")],
                [InlineKeyboardButton(text="✅ Всё же записаться на очный урок", url=f"https://t.me/{INSTAGRAM[1:]}")],
                [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")],
            ]
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        except Exception as e:
            logger.warning(f"Не удалось отправить followup self: {e}")


async def master_course_followup(user_id: int, chat_id: int, original_msg_id: int):
    """Через 90 сек, если пользователь не нажал — предложить онлайн-уроки"""
    await asyncio.sleep(90)
    if state_master_waiter.get(user_id):
        try:
            text = (
                "💡 <b>Пока думаешь — а может сначала онлайн?</b>\n\n"
                "Если не готова собрать компанию — попробуй сама за 199 ₽:\n"
                "🎬 <b>5 онлайн-уроков</b>:\n"
                "• Растушёванная стрелка (499 ₽)\n"
                "• Нежный коричневый смоки (499 ₽)\n"
                "• Смоки-айс (399 ₽)\n"
                "• Вечерний макияж (399 ₽)\n"
                "• Макияж из 4 средств (199 ₽)\n\n"
                "📦 Пакетом — <b>1 800 ₽</b> (экономия 200 ₽).\n\n"
                "👇 Посмотреть уроки:"
            )
            buttons = [
                [InlineKeyboardButton(text="🎬 Посмотреть онлайн-уроки", callback_data="online_lessons")],
                [InlineKeyboardButton(text="✅ Записаться на МК", url=f"https://t.me/{INSTAGRAM[1:]}")],
                [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")],
            ]
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        except Exception as e:
            logger.warning(f"Не удалось отправить followup master: {e}")


@router.callback_query(F.data.in_({"back_to_main", "cancel", "help"}))
async def clear_followup_state(callback: CallbackQuery):
    """Сбрасываем waiter при возврате/отмене — чтобы не отправлять followup"""
    state_self_waiter.pop(callback.from_user.id, None)
    state_master_waiter.pop(callback.from_user.id, None)
    await callback.answer()

# =========================
# FSM-состояния
# =========================

class BookingFlow(StatesGroup):
    """Состояния при записи на услугу"""
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()
    confirming = State()


class FeedbackFlow(StatesGroup):
    """Состояния при сборе отзыва"""
    rating = State()
    text = State()


class BonusFlow(StatesGroup):
    """Состояния при проверке баллов UDS"""
    entering_phone = State()


class ReferralFlow(StatesGroup):
    """Состояния для работы с реферальной программой"""
    entering_phone = State()


class PaymentFlow(StatesGroup):
    """Состояния при оплате онлайн-урока через Т‑Банк"""
    waiting_lesson = State()  # внутри state.data лежит order_id, lesson_key
    waiting_pack = State()    # внутри state.data лежит order_id


# =========================
# Клавиатуры
# =========================

def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню бота"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎀 Записаться на услугу", callback_data="book")],
        [InlineKeyboardButton(text="📚 Узнать про обучение", callback_data="education")],
        [InlineKeyboardButton(text="💄 Посмотреть услуги и цены", callback_data="services")],
        [InlineKeyboardButton(text="🎁 Подарок 500 ₽", callback_data="loyalty")],
        [InlineKeyboardButton(text="📞 Связаться с Марией", callback_data="contact")],
        [InlineKeyboardButton(text="🏠 Адрес студии", callback_data="address")],
        [InlineKeyboardButton(text="✍️ Оставить отзыв", callback_data="review")],
    ])


def services_kb() -> InlineKeyboardMarkup:
    """Список услуг по категориям"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💄 Макияж (все виды)", callback_data="cat_makeup")],
        [InlineKeyboardButton(text="💇‍♀️ Укладки и причёски", callback_data="cat_styling")],
        [InlineKeyboardButton(text="👁 Брови и ресницы", callback_data="cat_brows")],
        [InlineKeyboardButton(text="💆‍♀️ Шугаринг", callback_data="cat_shugaring")],
        [InlineKeyboardButton(text="🎀 Детям", callback_data="cat_kids")],
        [InlineKeyboardButton(text="🎁 Комплексные пакеты", callback_data="cat_packages")],
        [InlineKeyboardButton(text="🚗 Дополнительные услуги", callback_data="cat_extra")],
        [InlineKeyboardButton(text="📸 Посмотреть прайс с фото", callback_data="price_photo")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main")],
    ])


def date_kb() -> InlineKeyboardMarkup:
    """Выбор даты на ближайшие 7 дней"""
    buttons = []
    today = datetime.now()
    days_names = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    for i in range(7):
        d = today + timedelta(days=i)
        d_str = d.strftime("%d.%m")
        d_name = days_names[d.weekday()]
        buttons.append([
            InlineKeyboardButton(
                text=f"{d_name} {d_str}",
                callback_data=f"date_{d.strftime('%Y-%m-%d')}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад к выбору услуги", callback_data="back_to_service")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def time_kb() -> InlineKeyboardMarkup:
    """Выбор времени"""
    buttons = []
    row = []
    for slot in TIME_SLOTS:
        row.append(InlineKeyboardButton(text=slot, callback_data=f"time_{slot}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Назад к дате", callback_data="back_to_date")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение записи"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить запись", callback_data="confirm_yes")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="confirm_no")],
    ])


def education_kb() -> InlineKeyboardMarkup:
    """Меню обучения"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 Курс «Сам себе визажист»", callback_data="course_self")],
        [InlineKeyboardButton(text="🎬 6 онлайн-уроков", callback_data="online_lessons")],
        [InlineKeyboardButton(text="👩‍🏫 Мастер-класс", callback_data="course_master")],
        [InlineKeyboardButton(text="💬 Задать вопрос про обучение", callback_data="ask_education")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main")],
    ])


def contact_kb() -> InlineKeyboardMarkup:
    """Контактное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Позвонить", url=f"tel:{STUDIO_PHONE}")],
        [InlineKeyboardButton(text="✈️ Написать Марии в Telegram", url=f"https://t.me/{INSTAGRAM[1:]}")],
        [InlineKeyboardButton(text="🗺 Открыть в Яндекс Картах", url=MAPS_URL)],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main")],
    ])


def cancel_kb() -> ReplyKeyboardMarkup:
    """Клавиатура отмены"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_kb() -> ReplyKeyboardMarkup:
    """Пустая клавиатура для очистки"""
    return ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True)


# =========================
# Хэндлеры: основные команды
# =========================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработка /start"""
    await state.clear()
    
    text = (
        "👋 <b>Привет!</b>\n\n"
        "Я — помощник <b>Марии Федосеевой</b>, визажиста из Сызрани.\n\n"
        "Могу помочь тебе быстро и удобно:\n\n"
        "🎀 <b>Записаться на услугу</b> — макияж, укладку, брови\n"
        "📚 <b>Узнать про обучение</b> макияжу для себя\n"
        "💄 <b>Посмотреть прайс</b> и услуги\n"
        "🎁 <b>Забрать подарок 500 ₽</b> за первую процедуру\n"
        "🏠 <b>Подсказать адрес</b> и как добраться\n"
        "✍️ <b>Оставить отзыв</b> о последнем визите\n\n"
        "Что тебя интересует?"
    )
    await message.answer(text, reply_markup=main_menu_kb())


@router.callback_query(F.data == "register_uds")
async def register_uds(callback: CallbackQuery):
    """Отдельная кнопка регистрации в UDS (для приветственного сообщения)"""
    text = (
        "🎁 <b>Подарок 500 ₽</b>\n\n"
        "Запишись на любую процедуру — и <b>забери 500 ₽ в подарок</b>.\n\n"
        "Это твой <b>приветственный бонус</b> от студии Марии — "
        "без баллов, без кэшбэка: просто реальные 500 ₽, которые можно использовать сразу при записи.\n\n"
        "<b>Как получить:</b>\n\n"
        "1️⃣ <b>Выбери удобный способ регистрации</b> ниже\n"
        "2️⃣ <b>Запишись</b> на любую процедуру через бота\n"
        "3️⃣ <b>Сообщи менеджеру</b> при визите — подарок зачислится\n\n"
        "🔔 <b>ВАЖНО:</b> после регистрации <b>оставь уведомления включёнными</b> — "
        "тогда ты узнаешь о новых акциях и сертификатах первой и ничего не пропустишь."
    )
    buttons = [
        [InlineKeyboardButton(text="📲 Регистрация в приложении", url=UDS_REGISTER_LINKS["app"])],
        [InlineKeyboardButton(text="✈️ Регистрация через Telegram-бот", url=UDS_REGISTER_LINKS["tg"])],
        [InlineKeyboardButton(text="📱 Регистрация через MAX-бот", url=UDS_REGISTER_LINKS["max"])],
        [InlineKeyboardButton(text="🎁 Проверить баллы (если уже зарегистрирована)", callback_data="check_bonuses")],
        [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_main")],
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработка /help"""
    text = (
        "Я умею:\n\n"
        "/start — Главное меню\n"
        "/services — Услуги и цены\n"
        "/booking — Записаться на услугу\n"
        "/education — Про обучение макияжу\n"
        "/address — Адрес студии\n"
        "/contacts — Контакты\n"
        "/review — Оставить отзыв\n"
        "/cancel — Отменить текущее действие"
    )
    await message.answer(text, reply_markup=main_menu_kb())


@router.message(Command("cancel"))
@router.message(F.text.casefold().in_({"отменить", "❌ отменить"}))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена любого действия"""
    await state.clear()
    await message.answer(
        "Отменил. Если что-то ещё понадобится — нажми /start",
        reply_markup=remove_kb(),
    )


# =========================
# Главное меню: callback-обработчики
# =========================

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.answer(
        "Главное меню. Выбери, что тебе нужно:",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


# =========================
# Услуги и цены
# =========================

@router.callback_query(F.data == "services")
async def services_main(callback: CallbackQuery):
    """Показать категории услуг"""
    text = (
        "💄 <b>Услуги студии</b>\n\n"
        "Выбери категорию, чтобы посмотреть цены:"
    )
    await callback.message.edit_text(text, reply_markup=services_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("cat_"))
async def book_choose_category(callback: CallbackQuery, state: FSMContext):
    """Выбор категории → краткий прайс + запрос имени (правило 3 нажатий)"""
    cat = callback.data  # cat_makeup, cat_brows и т.д.

    category_names = {
        "cat_makeup": "💄 Макияж",
        "cat_styling": "💇 Укладки и причёски",
        "cat_brows": "👁 Брови и ресницы",
        "cat_shugaring": "🍯 Шугаринг",
        "cat_kids": "👶 Детям",
        "cat_packages": "🎁 Пакеты",
        "cat_extra": "➕ Дополнительно",
    }
    cat_name = category_names.get(cat, "Услуга")

    # Краткий прайс по категории
    cat_services = {
        "cat_makeup": ["makeup_day", "makeup_evening", "makeup_graphic", "makeup_bride", "makeup_bride_trial"],
        "cat_styling": ["styling_short", "styling_mid", "styling_long", "styling_collected", "styling_bride"],
        "cat_brows": ["lamination_brows", "lamination_lashes", "brows_correction", "brows_tint"],
        "cat_shugaring": ["shugaring_face", "shugaring_armpits", "shugaring_bikini", "shugaring_shins", "shugaring_thighs", "shugaring_legs_full"],
        "cat_kids": ["kids_styling"],
        "cat_packages": ["full_bridal", "express", "full_look"],
        "cat_extra": ["extra_home_visit", "extra_early_visit", "extra_before_6am"],
    }
    keys = cat_services.get(cat, [])
    price_lines = "\n".join(f"• {SERVICES[k]['name']} — {SERVICES[k]['price']}" for k in keys if k in SERVICES)

    await state.update_data(category=cat, category_name=cat_name)

    await callback.message.edit_text(
        f"<b>{cat_name}</b>\n\n"
        f"{price_lines}\n\n"
        f"Напиши, пожалуйста, <b>как тебя зовут</b>, чтобы Мария могла к тебе обратиться:"
    )
    await state.set_state(BookingFlow.entering_name)
    await callback.answer()


@router.callback_query(F.data == "price_photo")
async def price_photo(callback: CallbackQuery):
    """Отправляет 2 фото прайса (из сторис)"""
    await callback.answer()
    await callback.message.answer(
        "📸 <b>Прайс с фото</b>\n\n"
        "Сейчас пришлю 2 фото — основной прайс и отдельная страница про брови + шугаринг."
    )
    # Фото 1: основной прайс
    await callback.message.answer_photo(
        photo=FSInputFile("/workspace/bot_project/photos/price_list_main.jpg"),
        caption=(
            "💄 <b>Прайс — основная страница</b>\n\n"
            "Макияж, укладки, причёски, комплексные пакеты, обучение, лояльность, "
            "дополнительные услуги (выезд, ранний выезд).\n\n"
            "<i>Открой фото и приблизь — все цены читаются.</i>"
        )
    )
    await asyncio.sleep(0.5)
    # Фото 2: брови и шугаринг
    await callback.message.answer_photo(
        photo=FSInputFile("/workspace/bot_project/photos/price_list_brows_sugar.jpg"),
        caption=(
            "👁 <b>Брови и шугаринг</b>\n\n"
            "Коррекция пинцетом, окрашивание + коррекция, "
            "ламинирование бровей и ресниц, шугаринг всех зон.\n\n"
            "<i>Хочешь записаться — жми /start → Записаться.</i>"
        )
    )


# =========================
# Запись на услугу
# =========================

@router.callback_query(F.data == "book")
async def book_start(callback: CallbackQuery, state: FSMContext):
    """Начать запись — выбор услуги"""
    logger.info(f"🔥 CALLBACK book от {callback.from_user.id}: {callback.data}")
    text = (
        "🎀 <b>Запись на услугу</b>\n\n"
        "Выбери категорию услуг, на которую хочешь записаться:"
    )
    await callback.message.edit_text(text, reply_markup=services_kb())
    await state.set_state(BookingFlow.choosing_service)
    await callback.answer()


# Категории услуг, для которых нужно указывать время (макияж, укладки, пакеты)
# Для бровей / шугаринга / детям — только дата.
NEEDS_TIME_CATEGORIES = {"cat_makeup", "cat_styling", "cat_packages"}





@router.callback_query(F.data.startswith("date_"), StateFilter(BookingFlow.choosing_date))
async def book_choose_date(callback: CallbackQuery, state: FSMContext):
    """Сохранение даты; запрос времени (если нужно) или имени"""
    date_str = callback.data.replace("date_", "")
    await state.update_data(date=date_str)

    d = datetime.strptime(date_str, "%Y-%m-%d")
    days_names = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    formatted = f"{days_names[d.weekday()]} {d.strftime('%d.%m.%Y')}"

    data = await state.get_data()
    needs_time = data.get("needs_time", True)

    if needs_time:
        # Макияж / укладка / пакет — спрашиваем время
        text = (
            f"Дата: <b>{formatted}</b>\n\n"
            f"Во сколько тебе нужно быть готовой? Выбери удобное время:"
        )
        await callback.message.edit_text(text, reply_markup=time_kb())
        await state.set_state(BookingFlow.choosing_time)
    else:
        # Брови / шугаринг / детям — сразу к имени
        await callback.message.edit_text(
            f"Дата: <b>{formatted}</b>\n\n"
            f"Отлично! Теперь напиши, пожалуйста, <b>как тебя зовут</b>:"
        )
        await state.set_state(BookingFlow.entering_name)
    await callback.answer()


@router.callback_query(F.data.startswith("time_"), StateFilter(BookingFlow.choosing_time))
async def book_choose_time(callback: CallbackQuery, state: FSMContext):
    """Сохранение времени, запрос имени"""
    time_str = callback.data.replace("time_", "")
    await state.update_data(time=time_str)
    
    text = (
        f"Время: <b>{time_str}</b>\n\n"
        f"Отлично! Теперь напиши, пожалуйста, <b>как тебя зовут</b>:"
    )
    await callback.message.edit_text(text)
    await state.set_state(BookingFlow.entering_name)
    await callback.answer()


@router.message(StateFilter(BookingFlow.entering_name))
async def book_get_name(message: Message, state: FSMContext):
    """Получение имени, запрос телефона"""
    name = message.text.strip()
    
    if len(name) < 2 or len(name) > 50:
        await message.answer("Имя должно быть от 2 до 50 символов. Попробуй ещё раз:")
        return
    
    await state.update_data(name=name)

    await message.answer(
        f"Приятно познакомиться, <b>{name}</b>! 💛\n\n"
        f"Напиши свой <b>номер телефона</b>, чтобы Мария могла связаться:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Поделиться номером", request_contact=True)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )
    await state.set_state(BookingFlow.entering_phone)


@router.message(StateFilter(BookingFlow.entering_phone), F.contact)
async def book_get_phone_contact(message: Message, state: FSMContext):
    """Получение телефона через контакт"""
    logger.info(f"📞 book_get_phone_contact: contact={message.contact}")
    if message.contact and message.contact.phone_number:
        phone = message.contact.phone_number
        logger.info(f"📞 contact.phone_number={phone}, вызываю process_phone")
        await process_phone(message, state, phone)
    else:
        logger.warning(f"📞 contact пустой или без phone_number, fallback на text")


@router.message(StateFilter(BookingFlow.entering_phone))
async def book_get_phone_text(message: Message, state: FSMContext):
    """Получение телефона вручную"""
    logger.info(f"📞 book_get_phone_text: text={message.text!r}, contact={message.contact}")
    if message.contact:
        # Дубликат на случай если contact-фильтр не сработал
        phone = message.contact.phone_number or ""
        if phone:
            logger.info(f"📞 text-хэндлер поймал контакт, phone={phone}")
            await process_phone(message, state, phone)
            return
    phone = (message.text or "").strip()
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 10:
        await message.answer("Похоже, в номере ошибка. Попробуй ещё раз:")
        return
    await process_phone(message, state, phone)


async def process_phone(message: Message, state: FSMContext, phone: str):
    """Обработка телефона → сразу уведомление и финальное сообщение"""
    logger.info(f"🔔 process_phone START: phone={phone}, user_id={message.from_user.id}")
    await state.update_data(phone=phone)
    data = await state.get_data()
    await state.clear()
    logger.info(f"🔔 process_phone: state cleared, data={data}")

    # Уведомляем админа — громкий сигнал + кнопки
    if ADMIN_CHAT_ID:
        clean_phone = "".join(c for c in phone if c.isdigit() or c == "+")
        # tel: не работает в Telegram inline-кнопках — используем wa.me
        wa_link = f"https://wa.me/{clean_phone.lstrip('+')}"

        cat_name = data.get("category_name", "—")

        admin_text = (
            f"❗️❗️❗️ <b>НОВАЯ ЗАЯВКА НА ЗАПИСЬ</b> ❗️❗️❗️\n\n"
            f"🎀 Категория: <b>{cat_name}</b>\n"
            f"👤 Имя: <b>{data['name']}</b>\n"
            f"📞 Телефон: <b>{phone}</b>\n"
            f"💬 Telegram: @{message.from_user.username or '—'}\n"
            f"🆔 ID: <code>{message.from_user.id}</code>\n\n"
            f"⏰ Заявка пришла: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"<i>Уточни услугу и время при звонке</i>"
        )
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📞 {phone}", url=wa_link)],
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"admin_accept_{message.from_user.id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_{message.from_user.id}"),
            ],
        ])
        try:
            sent = await bot.send_message(
                ADMIN_CHAT_ID,
                admin_text,
                reply_markup=admin_kb,
                disable_notification=False,
            )
            logger.info(f"✅ admin notify sent: msg_id={sent.message_id}, chat={ADMIN_CHAT_ID}")
        except Exception as e:
            logger.error(f"❌ admin notify failed: {type(e).__name__}: {e}")

    # Дубль push-уведомлением на телефон через ntfy.sh
    logger.info(f"📲 notify_push: topic={NOTIFY_TOPIC}")
    await notify_push(
        title=f"🔔 Заявка: {data['name']}",
        body=f"{phone}\n{cat_name}\nУточни услугу и время",
        priority="high",
    )
    logger.info(f"📲 notify_push done")

    try:
        maria_url = f"https://t.me/{(INSTAGRAM[1:] if INSTAGRAM.startswith('@') else INSTAGRAM)}"
    except Exception:
        maria_url = "https://t.me/marrifedoseeva"

    await message.answer(
        f"Спасибо, <b>{data['name']}</b>! 💛\n\n"
        f"Проверяем свободные места.\n"
        f"Мария свяжется с вами для подтверждения записи.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Написать Марии в Telegram", url=maria_url)]
        ]),
    )
    # Убираем reply-клавиатуру (Поделиться номером)
    await message.answer("Если хочешь — можешь вернуться в меню:", reply_markup=main_menu_kb())


@router.callback_query(F.data == "confirm_yes", StateFilter(BookingFlow.confirming))
async def book_confirm_yes(callback: CallbackQuery, state: FSMContext):
    """Подтверждение записи, отправка админу"""
    data = await state.get_data()
    await state.clear()

    # Уведомляем админа
    if ADMIN_CHAT_ID:
        d = datetime.strptime(data["date"], "%Y-%m-%d")
        days_names = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
        formatted_date = f"{days_names[d.weekday()]} {d.strftime('%d.%m.%Y')}"

        needs_time = data.get("needs_time", True)
        time_line = f"Время: <b>{data.get('time', '—')}</b>\n" if needs_time else ""

        admin_text = (
            f"🔔 <b>Новая запись через бота</b>\n\n"
            f"Услуга: <b>{data['service_name']}</b>\n"
            f"Дата: <b>{formatted_date}</b>\n"
            f"{time_line}"
            f"Стоимость: <b>{data['service_price']}</b>\n"
            f"Имя: {data['name']}\n"
            f"Телефон: {data['phone']}\n"
            f"Клиент: @{callback.from_user.username or '—'}\n"
            f"ID: {callback.from_user.id}"
        )
        try:
            await bot.send_message(ADMIN_CHAT_ID, admin_text)
        except Exception as e:
            logger.error(f"Не удалось уведомить админа: {e}")

    needs_time = data.get("needs_time", True)
    time_line = f"🕐 {data.get('time', '')}\n" if needs_time and data.get("time") else ""

    await callback.message.edit_text(
        f"✅ <b>Запись подтверждена!</b>\n\n"
        f"<b>{data['service_name']}</b>\n"
        f"📅 {data['date']}\n"
        f"{time_line}"
        f"\nМария свяжется с тобой для подтверждения.\n"
        f"Если что-то нужно изменить — напиши Марии лично: {INSTAGRAM}",
        reply_markup=main_menu_kb(),
    )
    # Сразу отправляем кнопку для перехода в личку Марии
    try:
        maria_url = f"https://t.me/{(INSTAGRAM[1:] if INSTAGRAM.startswith('@') else INSTAGRAM)}"
    except Exception:
        maria_url = "https://t.me/marrifedoseeva"
    await callback.message.answer(
        "💬 <b>Связаться с Марией напрямую:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Написать Марии в Telegram", url=maria_url)]
        ])
    )
    await callback.answer("Готово!")


@router.callback_query(F.data == "confirm_no", StateFilter(BookingFlow.confirming))
async def book_confirm_no(callback: CallbackQuery, state: FSMContext):
    """Отмена записи"""
    await state.clear()
    await callback.message.answer(
        "Запись отменена. Если передумаешь — снова жми /start",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


# =========================
# Навигация назад в процессе записи
# =========================

@router.callback_query(F.data == "back_to_service", StateFilter(BookingFlow))
async def back_to_service_choice(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору услуги"""
    text = "Выбери категорию услуг:"
    await callback.message.edit_text(text, reply_markup=services_kb())
    await state.set_state(BookingFlow.choosing_service)
    await callback.answer()


@router.callback_query(F.data == "back_to_date", StateFilter(BookingFlow))
async def back_to_date_choice(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору даты"""
    text = "Выбери удобную дату:"
    await callback.message.edit_text(text, reply_markup=date_kb())
    await state.set_state(BookingFlow.choosing_date)
    await callback.answer()


# =========================
# Обучение
# =========================

@router.callback_query(F.data == "education")
async def education_main(callback: CallbackQuery):
    """Меню обучения"""
    text = (
        "📚 <b>Обучение макияжу</b>\n\n"
        "Мария преподаёт с нуля и для опытных.\n\n"
        "Хочешь научиться делать стойкий макияж сама себе "
        "и экономить 15-20 тысяч в месяц на визажисте?\n\n"
        "Выбери формат, который тебе ближе:"
    )
    await callback.message.edit_text(text, reply_markup=education_kb())
    await callback.answer()



# =========================
# Т‑Банк Оплата (EACQ API v2)
# =========================

TBANK_API_URL = "https://securepay.tinkoff.ru/v2"


def _tbank_token(params: dict, password: str) -> str:
    """SHA-256 токен для Т‑Банк: конкатенация значений по алфавиту ключей + пароль в начало."""
    flat = {k: v for k, v in params.items()
            if k not in ("Receipt", "Shops", "Receipts", "DATA", "Route")}
    sorted_vals = [str(flat[k]) for k in sorted(flat.keys())]
    return hashlib.sha256((password + "".join(sorted_vals)).encode("utf-8")).hexdigest()


def _tbank_creds() -> tuple[str, str]:
    """Возвращает (TerminalKey, Password) — тест или бой."""
    if os.getenv("TBANK_TEST_MODE", "1") == "1":
        return os.getenv("TBANK_TERMINAL_KEY_TEST", ""), os.getenv("TBANK_PASSWORD_TEST", "")
    return os.getenv("TBANK_TERMINAL_KEY_LIVE", ""), os.getenv("TBANK_PASSWORD_LIVE", "")


async def tbank_init(amount_rub: int, order_id: str, description: str,
                    customer_email: str = "", customer_phone: str = "",
                    success_url: str = "https://t.me/MariyaFedoseevaHelp_bot") -> dict | None:
    """Создать платёж. amount_rub — в рублях. Возвращает JSON или None."""
    term, pwd = _tbank_creds()
    params = {
        "TerminalKey": term,
        "Amount": amount_rub * 100,  # в копейках
        "OrderId": order_id,
        "Description": description[:140],
        "SuccessURL": success_url,
        "FailURL": success_url,
        "CustomerKey": order_id,
    }
    if customer_email:
        params["Receipt"] = {
            "Email": customer_email,
            "Taxation": "usn_income",
            "Items": [{
                "Name": description[:64],
                "Quantity": 1.0,
                "Amount": amount_rub * 100,
                "Price": amount_rub * 100,
                "Tax": "none",
                "PaymentMethod": "full_payment",
                "PaymentObject": "service",
            }],
        }
    elif customer_phone:
        params["Receipt"] = {
            "Phone": customer_phone,
            "Taxation": "usn_income",
            "Items": [{
                "Name": description[:64],
                "Quantity": 1.0,
                "Amount": amount_rub * 100,
                "Price": amount_rub * 100,
                "Tax": "none",
                "PaymentMethod": "full_payment",
                "PaymentObject": "service",
            }],
        }
    params["Token"] = _tbank_token(params, pwd)
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
            async with s.post(f"{TBANK_API_URL}/Init", json=params) as r:
                return await r.json()
    except Exception as e:
        logger.error(f"T-Bank Init error: {e}")
        return None


async def tbank_get_state(order_id: str) -> dict | None:
    """Проверить статус платежа. Возвращает JSON или None."""
    term, pwd = _tbank_creds()
    params = {"TerminalKey": term, "OrderId": order_id}
    params["Token"] = _tbank_token(params, pwd)
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
            async with s.post(f"{TBANK_API_URL}/GetState", json=params) as r:
                return await r.json()
    except Exception as e:
        logger.error(f"T-Bank GetState error: {e}")
        return None


# =========================
# Онлайн-уроки — закрытые каналы с доступом по пригласительной ссылке
# =========================

LESSONS_CHANNELS = {
    "arrow": {
        "name": "Растушёванная стрелка",
        "price": 499,
        "chat_id": -1004471472886,
    },
    "soft_smoky": {
        "name": "Нежный коричневый Смоки",
        "price": 499,
        "chat_id": -1004355469349,
    },
    "smoky": {
        "name": "Смоки-айс в классической теневой технике",
        "price": 399,
        "chat_id": -1003870443557,
    },
    "evening": {
        "name": "Вечерний макияж на скотч",
        "price": 399,
        "chat_id": -1004204414979,
    },
    "4_products": {
        "name": "Макияж из 4 средств",
        "price": 199,
        "chat_id": -1004364575592,
    },
    "curls": {
        "name": "Локоны на короткие и средние волосы",
        "price": 199,
        "chat_id": -1003935023965,
    },
}

PACK_PRICE = 1500


def online_lessons_kb() -> InlineKeyboardMarkup:
    """Кнопки отдельных онлайн-уроков"""
    buttons = []
    for key, lesson in LESSONS_CHANNELS.items():
        text = f"🎬 {lesson['name']} — {lesson['price']} ₽"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"buy_lesson_{key}")])
    buttons.append([InlineKeyboardButton(text=f"🎁 Пакет «Всё включено» — {PACK_PRICE} ₽", callback_data="buy_pack")])
    buttons.append([InlineKeyboardButton(text="⬅️ К обучению", callback_data="education")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "online_lessons")
async def show_online_lessons(callback: CallbackQuery):
    """Показать онлайн-уроки"""
    text = (
        "🎬 <b>Онлайн-уроки Марии Федосеевой</b>\n\n"
        "Покупай урок и получай пожизненный доступ к закрытому Telegram-каналу с уроком.\n\n"
        "<b>Отдельные уроки:</b>\n"
    )
    for key, lesson in LESSONS_CHANNELS.items():
        text += f"• {lesson['name']} — <b>{lesson['price']} ₽</b>\n"
    text += (
        "\n<b>🎁 Пакет «Всё включено» — 1 500 ₽</b>\n"
        "Все 6 уроков сразу. Экономия 996 ₽.\n\n"
        "Доступ — навсегда. Ссылка на канал одноразовая, для тебя лично."
    )
    await callback.message.edit_text(text, reply_markup=online_lessons_kb())
    await callback.answer()


async def create_invite(chat_id: int, user_id: int) -> str | None:
    """Создать одноразовую ссылку-приглашение"""
    try:
        # Генерируем уникальное имя ссылки для каждого пользователя
        link_name = f"user_{user_id}_{chat_id}"
        # Создаём invite link с лимитом 1 вход (member_limit=1)
        invite = await bot.create_chat_invite_link(
            chat_id=chat_id,
            name=link_name,
            member_limit=1,
            creates_join_request=False,
        )
        return invite.invite_link
    except Exception as e:
        logger.error(f"Ошибка создания invite для чата {chat_id}: {e}")
        return None


async def revoke_invite(chat_id: int, invite_link: str):
    """Отозвать ссылку-приглашение"""
    try:
        await bot.revoke_chat_invite_link(chat_id=chat_id, invite_link=invite_link)
    except Exception as e:
        logger.warning(f"Не удалось отозвать ссылку {invite_link}: {e}")


@router.callback_query(F.data.startswith("buy_lesson_"))
async def buy_single_lesson(callback: CallbackQuery, state: FSMContext):
    """Покупка одного урока — создание платежа в Т‑Банк"""
    lesson_key = callback.data.replace("buy_lesson_", "")
    lesson = LESSONS_CHANNELS.get(lesson_key)
    if not lesson:
        await callback.answer("Урок не найден", show_alert=True)
        return

    user_id = callback.from_user.id
    order_id = f"L-{lesson_key}-{user_id}-{int(time.time())}"

    result = await tbank_init(
        amount_rub=lesson["price"],
        order_id=order_id,
        description=f"Онлайн-урок «{lesson['name']}»",
    )
    if not result or not result.get("Success"):
        err = (result or {}).get("Message", "неизвестная ошибка")
        logger.error(f"T-Bank Init failed for order {order_id}: {result}")
        await callback.message.edit_text(
            f"😔 Не удалось создать платёж.\n\n"
            f"Напиши Марии — она поможет лично: {INSTAGRAM}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✈️ Написать Марии", url=f"https://t.me/{INSTAGRAM[1:]}")],
                [InlineKeyboardButton(text="⬅️ К урокам", callback_data="online_lessons")],
            ])
        )
        await callback.answer()
        return

    payment_url = result.get("PaymentURL")
    payment_id = result.get("PaymentId")
    await state.set_state(PaymentFlow.waiting_lesson)
    await state.update_data(order_id=order_id, lesson_key=lesson_key,
                            payment_id=payment_id, price=lesson["price"],
                            name=lesson["name"])

    text = (
        f"🎬 <b>Урок «{lesson['name']}»</b>\n\n"
        f"💰 Стоимость: <b>{lesson['price']} ₽</b>\n\n"
        f"Нажми кнопку ниже — откроется безопасная страница оплаты Т‑Банка.\n"
        f"После оплаты вернись сюда и нажми <b>«Я оплатила»</b> — "
        f"бот сразу пришлёт ссылку на закрытый канал.\n\n"
        f"🔒 Принимаем карты, СБП. Чеки — автоматически."
    )
    buttons = [
        [InlineKeyboardButton(text=f"💳 Оплатить {lesson['price']} ₽", url=payment_url)],
        [InlineKeyboardButton(text="✅ Я оплатила", callback_data="check_payment_lesson")],
        [InlineKeyboardButton(text="⬅️ К урокам", callback_data="online_lessons")],
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data == "buy_pack")
async def buy_all_lessons(callback: CallbackQuery, state: FSMContext):
    """Покупка пакета всех уроков — один платёж на 1500 ₽"""
    user_id = callback.from_user.id
    order_id = f"P-{user_id}-{int(time.time())}"

    result = await tbank_init(
        amount_rub=PACK_PRICE,
        order_id=order_id,
        description="Пакет «Всё включено» — 6 онлайн-уроков",
    )
    if not result or not result.get("Success"):
        logger.error(f"T-Bank Init failed for pack order {order_id}: {result}")
        await callback.message.edit_text(
            f"😔 Не удалось создать платёж.\n\n"
            f"Напиши Марии — она поможет лично: {INSTAGRAM}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✈️ Написать Марии", url=f"https://t.me/{INSTAGRAM[1:]}")],
                [InlineKeyboardButton(text="⬅️ К урокам", callback_data="online_lessons")],
            ])
        )
        await callback.answer()
        return

    payment_url = result.get("PaymentURL")
    payment_id = result.get("PaymentId")
    await state.set_state(PaymentFlow.waiting_pack)
    await state.update_data(order_id=order_id, payment_id=payment_id)

    text = (
        f"🎁 <b>Пакет «Всё включено»</b>\n\n"
        f"💰 Стоимость: <b>{PACK_PRICE} ₽</b> (экономия 996 ₽)\n\n"
        f"<b>В пакет входит 6 уроков:</b>\n"
    )
    for key, lesson in LESSONS_CHANNELS.items():
        text += f"• {lesson['name']}\n"
    text += (
        f"\nНажми кнопку ниже — откроется безопасная страница оплаты Т‑Банка.\n"
        f"После оплаты вернись и нажми <b>«Я оплатила»</b> — "
        f"бот пришлёт 6 личных ссылок на закрытые каналы.\n\n"
        f"🔒 Принимаем карты, СБП. Чеки — автоматически."
    )
    buttons = [
        [InlineKeyboardButton(text=f"💳 Оплатить {PACK_PRICE} ₽", url=payment_url)],
        [InlineKeyboardButton(text="✅ Я оплатила", callback_data="check_payment_pack")],
        [InlineKeyboardButton(text="⬅️ К урокам", callback_data="online_lessons")],
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.in_({"check_payment_lesson", "check_payment_pack"}))
async def check_payment(callback: CallbackQuery, state: FSMContext):
    """Проверить статус платежа в Т‑Банк и выдать ссылки если оплачено"""
    is_lesson = callback.data == "check_payment_lesson"
    user_id = callback.from_user.id
    data = await state.get_data()
    order_id = data.get("order_id")

    if not order_id:
        await callback.answer("Сессия оплаты истекла. Нажми «Купить» заново.", show_alert=True)
        return

    # Защита: order_id должен соответствовать user_id
    if str(user_id) not in order_id:
        await callback.answer("Чужая сессия оплаты.", show_alert=True)
        return

    await callback.answer("⏳ Проверяю оплату…")

    result = await tbank_get_state(order_id)
    if not result:
        await callback.message.answer("❌ Не удалось проверить оплату. Попробуй ещё раз через минуту.")
        return

    if not result.get("Success"):
        err = result.get("Message", "ошибка")
        logger.error(f"T-Bank GetState failed for {order_id}: {result}")
        await callback.message.answer(f"❌ Ошибка проверки: {err}")
        return

    status = result.get("Status", "")
    # T-Bank Status: NEW, FORM_SHOWED, DEADLINE_EXPIRED, CANCELED, PREAUTHORIZING,
    # AUTHORIZING, AUTHORIZED, REJECTED, AUTH_FAIL, CONFIRMED, PARTIAL_REFUNDED,
    # REFUNDED, REVERSED, CHECKING, 3DS_CHECKING, 3DS_CHECKED, COMPLETED
    if status not in ("CONFIRMED", "AUTHORIZED", "COMPLETED"):
        await callback.message.answer(
            f"⏳ Оплата ещё не поступила (статус: {status}).\n\n"
            f"Заверши оплату на странице Т‑Банка и нажми <b>«Я оплатила»</b> ещё раз.\n"
            f"Если уже оплатила — подожди 1–2 минуты и попробуй снова."
        )
        return

    # Оплата подтверждена — создаём ссылки
    if is_lesson:
        lesson_key = data.get("lesson_key")
        lesson = LESSONS_CHANNELS.get(lesson_key)
        if not lesson:
            await callback.message.answer("❌ Не найден урок. Напиши Марии.")
            return
        invite = await create_invite(lesson["chat_id"], user_id)
        if not invite:
            await callback.message.answer(
                f"✅ Оплата получена, но не удалось создать ссылку автоматически.\n"
                f"Напиши Марии — она пришлёт вручную: {INSTAGRAM}"
            )
            await state.clear()
            return
        amount = data.get("price", "?")
        await callback.message.edit_text(
            f"✅ <b>Оплата получена!</b>\n\n"
            f"🎬 <b>{lesson['name']}</b>\n\n"
            f"🔗 Твоя личная ссылка для входа:\n<code>{invite}</code>\n\n"
            f"⏳ Ссылка одноразовая — работает только для тебя.\n"
            f"Доступ к каналу — навсегда.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Перейти к уроку", url=invite)],
                [InlineKeyboardButton(text="⬅️ К урокам", callback_data="online_lessons")],
                [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")],
            ])
        )
        # Уведомление Маше
        try:
            user = callback.from_user
            username = f"@{user.username}" if user.username else f"id{user_id}"
            await bot.send_message(
                ADMIN_CHAT_ID,
                f"💰 <b>Новая оплата (тест: {os.getenv('TBANK_TEST_MODE','1')=='1'})</b>\n\n"
                f"🎬 Урок: {lesson['name']}\n"
                f"💵 Сумма: {amount} ₽\n"
                f"👤 Покупатель: {username}\n"
                f"🆔 OrderId: {order_id}\n"
                f"🔗 Ссылка: {invite}",
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить админа: {e}")
    else:
        # Пакет — 6 ссылок
        invites = []
        for key, lesson in LESSONS_CHANNELS.items():
            invite = await create_invite(lesson["chat_id"], user_id)
            invites.append((lesson["name"], invite))
        text_parts = [f"✅ <b>Оплата получена!</b>\n\n🎁 <b>Пакет «Всё включено»</b>\n\n🔗 <b>Твои 6 ссылок:</b>\n\n"]
        for name, invite in invites:
            if invite:
                text_parts.append(f"<b>{name}</b>\n{invite}\n\n")
            else:
                text_parts.append(f"❌ {name} — не создана\n\n")
        text_parts.append("⏳ Каждая ссылка одноразовая — только для тебя. Доступ — навсегда.")
        text_parts.append("\n\n💡 <i>Сохрани это сообщение — ссылки больше нигде не появятся.</i>")
        await callback.message.edit_text(
            "".join(text_parts),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ К урокам", callback_data="online_lessons")],
                [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")],
            ])
        )
        # Уведомление Маше
        try:
            user = callback.from_user
            username = f"@{user.username}" if user.username else f"id{user_id}"
            ok_count = sum(1 for _, i in invites if i)
            await bot.send_message(
                ADMIN_CHAT_ID,
                f"💰 <b>Новая оплата пакета (тест: {os.getenv('TBANK_TEST_MODE','1')=='1'})</b>\n\n"
                f"💵 Сумма: {PACK_PRICE} ₽\n"
                f"👤 Покупатель: {username}\n"
                f"🆔 OrderId: {order_id}\n"
                f"📊 Ссылок создано: {ok_count}/6",
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить админа: {e}")

    await state.clear()



@router.callback_query(F.data == "course_self")
async def course_self(callback: CallbackQuery):
    """Описание курса Сам себе визажист"""
    text = (
        "🎓 <b>Урок «Сам себе визажист»</b>\n\n"
        "Разбор <b>одного макияжа на выбор</b>:\n"
        "нюд · вечерний · смоки-айс · голливудский · растушёванная стрелка\n\n"
        "<b>На уроке разберём:</b>\n"
        "• Анатомию вашего лица — формы, объёмы, впадины\n"
        "• Какой макияж подойдёт именно под вашу внешность\n"
        "• Подготовку кожи к макияжу и подбор тона\n"
        "• Основы контуринга — скуловая коррекция, работа с объёмами\n"
        "• Архитектуру бровей под вашу форму\n"
        "• Как правильно красить и корректировать форму губ\n"
        "• Вашу косметичку: что взаимозаменяемо, как работать с кистями и ухаживать за ними\n\n"
        f"💰 <b>{COURSES['self']['price']}</b>\n"
        f"⏱ Длительность — <b>3,5–4 часа</b>, очно в студии."
    )
    buttons = [
        [InlineKeyboardButton(text="🎀 Записаться на урок", url=f"https://t.me/{INSTAGRAM[1:]}")],
        [InlineKeyboardButton(text="⬅️ К выбору формата", callback_data="education")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")],
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

    # Через 90 сек, если человек не кликнул — предложить онлайн-уроки
    state_self_waiter[callback.from_user.id] = True
    asyncio.create_task(self_course_followup(callback.from_user.id, callback.message.chat.id, callback.message.message_id))


@router.callback_query(F.data == "course_master")
async def course_master(callback: CallbackQuery):
    """Мастер-классы"""
    text = (
        "👯 <b>Мастер-класс по макияжу</b>\n\n"
        "Идеальный вариант для:\n"
        "• Девичника 🎉\n"
        "• Празднования дня рождения\n"
        "• Времени в хорошей компании\n\n"
        "Погрузитесь в мир красоты и научитесь делать макияж, "
        "тратя на него не более <b>10 минут</b>.\n\n"
        "Группа — до 10 человек.\n\n"
        "💰 <b>Взрослые</b> — 1 500 ₽\n"
        "💰 <b>Дети</b> — 1 000 ₽\n\n"
        "<i>Все материалы включены. Длительность — 2-3 часа.</i>"
    )
    buttons = [
        [InlineKeyboardButton(text="🎀 Записаться на МК", url=f"https://t.me/{INSTAGRAM[1:]}")],
        [InlineKeyboardButton(text="⬅️ К выбору формата", callback_data="education")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")],
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

    # Через 60 сек, если человек не кликнул — предложить онлайн-уроки
    state_master_waiter[callback.from_user.id] = True
    asyncio.create_task(master_course_followup(callback.from_user.id, callback.message.chat.id, callback.message.message_id))


@router.callback_query(F.data == "ask_education")
async def ask_education(callback: CallbackQuery):
    """Свободный вопрос про обучение"""
    text = (
        "Напиши свой вопрос Марии — она ответит в личке:\n\n"
        f"👉 {INSTAGRAM}"
    )
    buttons = [[InlineKeyboardButton(text="✈️ Открыть чат с Марией", url=f"https://t.me/{INSTAGRAM[1:]}")]]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


# =========================
# Контакты и адрес
# =========================

@router.callback_query(F.data == "contact")
async def contact_info(callback: CallbackQuery):
    """Контакты"""
    text = (
        f"📞 <b>Связаться со студией</b>\n\n"
        f"<b>Телефон:</b> {STUDIO_PHONE}\n"
        f"<b>Telegram:</b> {INSTAGRAM}\n"
        f"<b>Бот для записи:</b> @MariyaFedoseevaHelp_bot\n\n"
        f"Маша обычно отвечает в течение 30 минут в рабочее время."
    )
    await callback.message.edit_text(text, reply_markup=contact_kb())
    await callback.answer()


@router.callback_query(F.data == "address")
async def address_info(callback: CallbackQuery):
    """Адрес и время работы"""
    work_text = "\n".join([f"  {day}: {hours}" for day, hours in WORK_HOURS.items()])
    
    text = (
        f"🏠 <b>Студия находится</b>\n\n"
        f"📍 {STUDIO_ADDRESS}\n\n"
        f"<b>Часы работы:</b>\n{work_text}\n\n"
        f"Запись в студию — по предварительной записи."
    )
    buttons = [
        [InlineKeyboardButton(text="🗺 Открыть в Яндекс Картах", url=MAPS_URL)],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main")],
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


# =========================
# Отзывы
# =========================

@router.callback_query(F.data == "review")
async def review_start(callback: CallbackQuery, state: FSMContext):
    """Начало сбора отзыва"""
    text = (
        "✍️ <b>Спасибо, что делишься впечатлениями!</b>\n\n"
        "Оцени последний визит от 1 до 5 звёзд:"
    )
    buttons = []
    row = []
    for i in range(1, 6):
        row.append(InlineKeyboardButton(text=f"{'⭐' * i}", callback_data=f"rating_{i}"))
    buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(FeedbackFlow.rating)
    await callback.answer()


@router.callback_query(F.data.startswith("rating_"), StateFilter(FeedbackFlow.rating))
async def review_set_rating(callback: CallbackQuery, state: FSMContext):
    """Сохранение оценки"""
    rating = int(callback.data.replace("rating_", ""))
    await state.update_data(rating=rating)
    
    text = (
        f"Твоя оценка: <b>{'⭐' * rating}</b>\n\n"
        "Хочешь написать отзыв словами?\n"
        "(или нажми «Пропустить»)"
    )
    buttons = [
        [InlineKeyboardButton(text="💬 Написать отзыв", callback_data="write_review")],
        [InlineKeyboardButton(text="⏭ Пропустить и отправить", callback_data="skip_review")],
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data == "write_review", StateFilter(FeedbackFlow.rating))
async def review_ask_text(callback: CallbackQuery, state: FSMContext):
    """Запрос текста отзыва"""
    await callback.message.edit_text("Напиши свой отзыв одним сообщением:")
    await state.set_state(FeedbackFlow.text)
    await callback.answer()


@router.message(StateFilter(FeedbackFlow.text))
async def review_get_text(message: Message, state: FSMContext):
    """Получение текста отзыва, отправка админу"""
    text = message.text
    data = await state.get_data()
    await state.clear()
    
    if ADMIN_CHAT_ID:
        user = message.from_user
        admin_text = (
            f"📝 <b>Новый отзыв через бота</b>\n\n"
            f"Оценка: {'⭐' * data['rating']}\n"
            f"Текст: {text}\n\n"
            f"<b>От:</b> "
            f"@{user.username or '—'} "
            f"({user.first_name or ''} {user.last_name or ''})\n"
            f"ID: {user.id}"
        )
        try:
            await bot.send_message(ADMIN_CHAT_ID, admin_text)
        except Exception as e:
            logger.error(f"Не удалось отправить отзыв: {e}")
    
    await message.answer(
        "💛 <b>Спасибо за отзыв!</b>\n\n"
        "Если хочешь, чтобы отзыв также появился на Яндекс Картах — "
        "будет здорово! Это поможет другим женщинам найти Машу.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Оставить отзыв на Яндекс Картах", url=MAPS_URL)],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")],
        ])
    )


@router.callback_query(F.data == "skip_review", StateFilter(FeedbackFlow.rating))
async def review_skip_text(callback: CallbackQuery, state: FSMContext):
    """Пропуск текста отзыва"""
    data = await state.get_data()
    await state.clear()
    
    if ADMIN_CHAT_ID:
        user = callback.from_user
        admin_text = (
            f"📝 <b>Новый отзыв через бота</b>\n\n"
            f"Оценка: {'⭐' * data['rating']}\n"
            f"(без текста)\n\n"
            f"<b>От:</b> @{user.username or '—'}\n"
            f"ID: {user.id}"
        )
        try:
            await bot.send_message(ADMIN_CHAT_ID, admin_text)
        except Exception as e:
            logger.error(f"Не удалось отправить отзыв: {e}")
    
    await callback.message.edit_text(
        "💛 Спасибо за оценку!\n\n"
        "Если хочешь, можешь оставить отзыв на Яндекс Картах:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Оставить отзыв на Яндекс Картах", url=MAPS_URL)],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")],
        ])
    )
    await callback.answer()


# =========================
# Программа лояльности UDS
# =========================

@router.message(Command("bonuses"))
@router.callback_query(F.data == "loyalty")
async def cmd_bonuses(event, state: FSMContext):
    """Показать информацию о программе лояльности UDS"""
    if isinstance(event, CallbackQuery):
        await event.answer()
        target = event.message
    else:
        target = event
        await state.clear()
    
    text = (
        "🎁 <b>Подарок 500 ₽ за первую процедуру</b>\n\n"
        "Зарегистрируйся в программе лояльности студии Марии — "
        "и <b>забери 500 ₽ в подарок</b> сразу при первой процедуре.\n\n"
        "<b>Выбери удобный способ регистрации:</b>\n\n"
        "📲 <b>Приложение UDS</b> — для тех, кто любит наглядно\n"
        "✈️ <b>Telegram-бот</b> — если предпочитаешь Telegram\n"
        "📱 <b>MAX-бот</b> — если используешь MAX\n\n"
        "<b>Что даёт подарок:</b>\n\n"
        "🎁 <b>500 ₽ реальными деньгами</b> — не баллами, а именно рубли, "
        "которыми можно оплатить до 50% стоимости следующей процедуры\n\n"
        "🔔 <b>ВАЖНО:</b> после регистрации <b>оставь уведомления включёнными</b> — "
        "так ты узнаешь о новых акциях и сертификатах первой."
    )
    buttons = [
        [InlineKeyboardButton(text="📲 Зарегистрироваться (приложение)", url=UDS_REGISTER_LINKS["app"])],
        [InlineKeyboardButton(text="✈️ Зарегистрироваться через Telegram-бот", url=UDS_REGISTER_LINKS["tg"])],
        [InlineKeyboardButton(text="📱 Зарегистрироваться через MAX-бот", url=UDS_REGISTER_LINKS["max"])],
        [InlineKeyboardButton(text="👯 Пригласить подругу — получить 400 бонусов", callback_data="invite_friend")],
        [InlineKeyboardButton(text="🎁 У меня уже есть — проверить баллы", callback_data="check_bonuses")],
        [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_main")],
    ]
    
    if isinstance(event, CallbackQuery):
        await target.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await target.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data == "check_bonuses")
async def check_bonuses_start(callback: CallbackQuery, state: FSMContext):
    """Начало проверки баллов — запрос телефона"""
    await callback.message.edit_text(
        "🔍 <b>Проверка бонусов</b>\n\n"
        "Отправь свой номер телефона, который привязан к UDS-карте:\n\n"
        "Например: <code>+7 999 123-45-67</code>\n\n"
        "Маша увидит только обезличенный запрос — твои данные в безопасности.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Поделиться номером", callback_data="share_phone_bonuses")],
            [InlineKeyboardButton(text="⬅️ Назад к программе лояльности", callback_data="loyalty")],
        ])
    )
    await state.set_state(BonusFlow.entering_phone)
    await callback.answer()


@router.callback_query(F.data == "share_phone_bonuses", StateFilter(BonusFlow.entering_phone))
async def request_phone_for_bonuses(callback: CallbackQuery):
    """Запрос контакта через кнопку Telegram"""
    await callback.message.answer(
        "Нажми кнопку «Поделиться номером» ниже 👇",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Поделиться номером", request_contact=True)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )
    await callback.answer()


@router.message(StateFilter(BonusFlow.entering_phone), F.contact)
async def bonus_get_phone_contact(message: Message, state: FSMContext):
    """Получение телефона через контакт"""
    phone = message.contact.phone_number
    await check_uds_balance(message, state, phone)


@router.message(StateFilter(BonusFlow.entering_phone))
async def bonus_get_phone_text(message: Message, state: FSMContext):
    """Получение телефона вручную, проверка баллов"""
    phone = message.text.strip()
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 10:
        await message.answer("Похоже, в номере ошибка. Введи в формате +7 999 123-45-67:")
        return
    await check_uds_balance(message, state, phone)


async def check_uds_balance(message: Message, state: FSMContext, phone: str):
    """Проверка баллов через UDS API и вывод результата"""
    await state.clear()
    await message.answer("🔍 Проверяю…", reply_markup=remove_kb())
    
    api_key = open("/workspace/secrets/uds.key").read().strip()
    
    try:
        async with UDSClient(
            company_id="549756203475",
            api_key=api_key,
            silence_httpx_log=True,
        ) as client:
            # Нормализуем телефон
            digits = "".join(c for c in phone if c.isdigit())
            if not digits.startswith("7") and not digits.startswith("8"):
                digits = "7" + digits
            
            result = await client.customers.find(phone=digits)
            
            # result может быть list или один объект
            customers_list = result.rows if hasattr(result, "rows") else result
            if isinstance(customers_list, list) and customers_list:
                customer = customers_list[0]
            elif customers_list:
                customer = customers_list
            else:
                customer = None
            
            if customer:
                p = customer.participant
                tier_name = p.membership_tier.name if hasattr(p.membership_tier, "name") else "Гость"
                points = int(p.points or 0)
                total_spent = int(p.cash_spent or 0)
                operations = int(p.operations_count or 0)
                invited = int(p.invited_count or 0)
                
                result_text = (
                    f"💳 <b>Твой профиль UDS</b>\n\n"
                    f"👤 <b>{customer.display_name}</b>\n"
                    f"📱 {phone}\n\n"
                    f"💰 <b>Баллов сейчас:</b> <code>{points}</code>\n"
                    f"📊 Потрачено в студии: <code>{total_spent:,} ₽</code>\n"
                    f"🏅 Уровень: <b>{tier_name}</b>\n"
                    f"🎯 Визитов: <b>{operations}</b>\n"
                    f"👯 Привела подруг: <b>{invited}</b>\n\n"
                )
                
                # Подсказки по уровням
                if tier_name == "Гость":
                    if total_spent >= 25000 or invited >= 3:
                        result_text += (
                            "🎉 Поздравляю! У вас накоплены бонусы для перехода "
                            "на уровень «Красотка» — обратитесь к Марии для "
                            "подтверждения повышения!"
                        )
                    else:
                        need_money = 25000 - total_spent
                        result_text += (
                            f"💡 До уровня «Красотка» (5% кэшбэк): "
                            f"потратьте ещё <b>{need_money:,} ₽</b>\n"
                            f"Или приведите 3 подруги."
                        )
                elif tier_name == "Красотка":
                    if total_spent >= 50000 or invited >= 5:
                        result_text += "🎉 Вы на пороге уровня «VIP»! Продолжайте в том же духе."
                    else:
                        need_money = 50000 - total_spent
                        result_text += (
                            f"💡 До уровня «VIP» (7% кэшбэк): "
                            f"потратьте ещё <b>{need_money:,} ₽</b>\n"
                            f"Или приведите ещё {5 - invited} подруг."
                        )
                elif tier_name == "VIP":
                    result_text += "👑 Вы — VIP клиент! Максимальный кэшбэк 7% и списание 10%."
                
                buttons = [
                    [InlineKeyboardButton(text="🎀 Записаться на услугу", callback_data="book")],
                    [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")],
                ]
                
                await message.answer(
                    result_text,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                )
            else:
                # Не найден — предлагаем регистрацию
                result_text = (
                    f"🤔 Клиент с номером <code>{phone}</code> не найден в нашей базе.\n\n"
                    f"Зарегистрируйся за 1 минуту — и получи <b>500 бонусов</b> в подарок.\n\n"
                    f"<b>Выбери удобный способ:</b>\n\n"
                    f"🔔 <b>Важно:</b> после регистрации <b>оставь уведомления включёнными</b> — "
                    f"чтобы быть в курсе акций, скидок и сертификатов."
                )
                buttons = [
                    [InlineKeyboardButton(text="📲 Зарегистрироваться в приложении UDS", url=UDS_REGISTER_LINKS["app"])],
                    [InlineKeyboardButton(text="✈️ Через Telegram-бот", url=UDS_REGISTER_LINKS["tg"])],
                    [InlineKeyboardButton(text="📱 Через MAX-бот", url=UDS_REGISTER_LINKS["max"])],
                    [InlineKeyboardButton(text="✈️ Или напиши Марии лично", url=f"https://t.me/{INSTAGRAM[1:]}")],
                    [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")],
                ]
                await message.answer(
                    result_text,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                )
    except Exception as e:
        logger.error(f"Ошибка проверки UDS: {e}", exc_info=True)
        await message.answer(
            "⚠️ Не получилось проверить бонусы прямо сейчас.\n\n"
            "Попробуй позже или напиши Марии в личку — она подскажет баланс: " + INSTAGRAM,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✈️ Написать Марии", url=f"https://t.me/{INSTAGRAM[1:]}")],
                [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")],
            ])
        )


# =========================
# Реферальная программа
# =========================

# Глобальные данные реферальной программы из UDS
REFERRAL_REWARD = 400  # баллов за привод подруги
REFERRAL_CASHBACK_FIRST = 5  # % кэшбэка с первой покупки
REFERRAL_CASHBACK_RECURRING = 1  # % кэшбэка с последующих покупок


@router.callback_query(F.data == "invite_friend")
async def invite_friend_start(callback: CallbackQuery, state: FSMContext):
    """Начало — попросить телефон, чтобы дать ссылку"""
    text = (
        "👯 <b>Пригласи подругу — заработай 400 баллов</b>\n\n"
        f"За каждого нового клиента, который зарегистрируется по твоей ссылке и "
        f"сделает первую покупку, ты получишь:\n\n"
        "✅ <b>400 баллов</b> на свой бонусный счёт\n"
        "✅ <b>5% кэшбэка</b> с её первой покупки\n"
        "✅ <b>1% кэшбэка</b> с её последующих покупок\n\n"
        "Чтобы дать ссылку для твоего профиля — мне нужно найти тебя в базе.\n\n"
        "Отправь номер телефона, который привязан к UDS-карте:"
    )
    buttons = [
        [InlineKeyboardButton(text="📱 Поделиться номером", callback_data="share_phone_referral")],
        [InlineKeyboardButton(text="📸 Инструкция с фото (3 шага)", callback_data="invite_howto")],
        [InlineKeyboardButton(text="⬅️ Назад к программе лояльности", callback_data="loyalty")],
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(ReferralFlow.entering_phone)
    await callback.answer()


@router.callback_query(F.data == "share_phone_referral", StateFilter(ReferralFlow.entering_phone))
async def request_phone_for_referral(callback: CallbackQuery):
    """Кнопка поделиться номером"""
    await callback.message.answer(
        "Нажми кнопку «Поделиться номером» ниже 👇",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Поделиться номером", request_contact=True)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )
    await callback.answer()


@router.message(StateFilter(ReferralFlow.entering_phone), F.contact)
async def referral_get_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await process_referral(message, state, phone)


@router.message(StateFilter(ReferralFlow.entering_phone))
async def referral_get_text(message: Message, state: FSMContext):
    phone = message.text.strip()
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 10:
        await message.answer("Похоже, в номере ошибка. Введи в формате +7 999 123-45-67:")
        return
    await process_referral(message, state, phone)


async def process_referral(message: Message, state: FSMContext, phone: str):
    """Получаем персональную реферальную ссылку клиента"""
    await state.clear()
    await message.answer("🔍 Ищу тебя в базе…", reply_markup=remove_kb())
    
    api_key = open("/workspace/secrets/uds.key").read().strip()
    
    try:
        async with UDSClient(
            company_id="549756203475",
            api_key=api_key,
            silence_httpx_log=True,
        ) as client:
            digits = "".join(c for c in phone if c.isdigit())
            if not digits.startswith("7") and not digits.startswith("8"):
                digits = "7" + digits
            
            result = await client.customers.find(phone=digits)
            
            customers_list = result.rows if hasattr(result, "rows") else result
            if isinstance(customers_list, list) and customers_list:
                customer = customers_list[0]
            elif customers_list:
                customer = customers_list
            else:
                customer = None
            
            if customer:
                p = customer.participant
                invited = int(p.invited_count or 0)
                points = int(p.points or 0)
                
                # Генерируем ссылку — slug Маши (fedoseeva) + персональный код клиента
                slug = "fedoseeva"
                customer_uid = customer.uid or str(p.id)
                customer_id = p.id
                
                # Несколько вариантов ссылки
                # Пытаемся по структуре Telegram:
                # 1. По универсальной реферальной ссылке студии
                # 2. По персональному коду через Telegram-бот Маши
                
                personal_app_url = f"https://{slug}.uds.app/c/join?ref=cvpv5571"
                personal_tg_url = UDS_REGISTER_LINKS["tg"] + f"&inviter={customer_id}" if "?" in UDS_REGISTER_LINKS["tg"] else UDS_REGISTER_LINKS["tg"] + f"?start=cvpv5571_inviter_{customer_id}"
                
                text = (
                    f"💛 <b>{customer.display_name}</b>, вот твоя ссылка для приглашений!\n\n"
                    f"<b>Что ты получишь за каждую подругу:</b>\n"
                    f"🎁 <b>400 баллов</b> на твой счёт\n"
                    f"💸 <b>5%</b> кэшбэка с её первой покупки\n"
                    f"💸 <b>1%</b> с её последующих покупок\n\n"
                    f"📊 <b>Уже привела:</b> {invited} подруг\n"
                    f"💰 <b>Заработано бонусов:</b> {invited * REFERRAL_REWARD} ₽\n\n"
                    f"<b>📲 Как пригласить (отправь подруге):</b>\n\n"
                    f"<b>Сообщение можно скопировать:</b>\n"
                    f"<blockquote>"
                    f"Привет! 👯 Подруга посоветовала студию Марии Федосеевой в Сызрани. "
                    f"Регистрируйся по моей ссылке — тебе +500 бонусов, а мне ещё +400 💛\n"
                    f"{personal_app_url}"
                    f"</blockquote>\n\n"
                    f"<b>Или просто кнопки для отправки:</b>"
                )
                
                buttons = [
                    [InlineKeyboardButton(text="📲 Отправить лично подруге", url=f"https://t.me/share/url?url={personal_app_url}&text=Ссылка%20для%20регистрации%20в%20UDS")],
                    [InlineKeyboardButton(text="✈️ Отправить через Telegram", url=UDS_REGISTER_LINKS["tg"])],
                    [InlineKeyboardButton(text="📲 Открыть UDS-приложение", url=personal_app_url)],
                ]
                buttons.append([InlineKeyboardButton(text="📸 Инструкция с фото (3 шага)", callback_data="invite_howto")])
                buttons.append([InlineKeyboardButton(text="⬅️ Назад к программе", callback_data="loyalty")])

                await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
            else:
                # Клиента нет в базе
                text = (
                    f"🤔 Не нашла тебя в базе по номеру <code>{phone}</code>.\n\n"
                    "Сначала зарегистрируйся, потом сможешь приглашать."
                )
                buttons = [
                    [InlineKeyboardButton(text="📲 Зарегистрироваться", url=UDS_REGISTER_LINKS["app"])],
                    [InlineKeyboardButton(text="⬅️ Назад к программе", callback_data="loyalty")],
                ]
                await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    
    except Exception as e:
        logger.error(f"Ошибка реферала: {e}", exc_info=True)
        # Фоллбэк — даём общую ссылку и инструкцию
        text = (
            "👯 <b>Пригласи подругу</b>\n\n"
            "Скинь ей эту ссылку для регистрации:\n\n"
            f"👉 {UDS_REGISTER_LINKS['app']}\n\n"
            "Когда она зарегистрируется и сделает первую покупку — "
            "тебе автоматически зачислятся +400 баллов.\n\n"
            "Технические неполадки — покажи Марии, она подтвердит вручную."
        )
        buttons = [
            [InlineKeyboardButton(text="📲 Открыть UDS-приложение", url=UDS_REGISTER_LINKS["app"])],
            [InlineKeyboardButton(text="⬅️ Назад к программе", callback_data="loyalty")],
        ]
        await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


# =========================
# Echo-fallback
# =========================

@router.message()
async def echo_fallback(message: Message):
    """Если непонятно, что написано"""
    text = (
        "Не совсем поняла, что ты имеешь в виду.\n\n"
        "Можешь выбрать действие из меню:"
    )
    await message.answer(text, reply_markup=main_menu_kb())


# =========================
# Инструкция: как пригласить подругу (3 фото)
# =========================

@router.callback_query(F.data == "invite_howto")
async def send_invite_howto(callback: CallbackQuery):
    """Отправляет одну картинку со всеми 3 шагами инструкции"""
    await callback.answer("📸 Отправляю инструкцию…")
    await callback.message.answer(
        "📸 <b>Пошаговая инструкция — как пригласить подругу через UDS</b>\n\n"
        "Сейчас пришлю одну картинку со всеми 3 шагами. "
        "Она открывается в полный размер — нажми на неё, чтобы рассмотреть детали."
    )
    
    await callback.message.answer_photo(
        photo=FSInputFile("/workspace/cert_gift/all_steps_one_image.png"),
        caption=(
            "👆 <b>4 шага:</b>\n\n"
            "1️⃣ На главной → квадратик <b>«Мои компании»</b>\n"
            "2️⃣ В списке → найди <b>«Студия Марии…»</b>\n"
            "3️⃣ На странице студии → <b>«Рекомендуйте»</b>\n"
            "4️⃣ На странице рекомендаций → <b>«Рекомендовать»</b> или QR-код\n\n"
            "За каждого нового клиента — <b>+400 баллов</b> тебе и <b>+500</b> подруге!"
        )
    )
    
    await callback.message.answer(
        "🎁 <b>После шага 4 — что увидишь:</b>\n\n"
        "📋 <b>Ссылку</b> — её можно скопировать и отправить подруге в любом мессенджере.\n\n"
        "📱 <b>QR-код</b> — покажи его подруге при встрече, она отсканирует камерой телефона.\n\n"
        "💡 <i>Если подруга далеко — лучше скопировать ссылку. Если встречаетесь — показать QR.</i>"
    )


# =========================
# Запуск
# =========================

async def on_startup():
    """При старте"""
    # Установка команд бота
    commands = [
        {"command": "start", "description": "Главное меню"},
        {"command": "services", "description": "Услуги и цены"},
        {"command": "booking", "description": "Записаться на услугу"},
        {"command": "education", "description": "Обучение макияжу"},
        {"command": "address", "description": "Адрес студии"},
        {"command": "contacts", "description": "Контакты"},
        {"command": "review", "description": "Оставить отзыв"},
        {"command": "bonuses", "description": "Бонусы UDS"},
        {"command": "help", "description": "Помощь по командам"},
        {"command": "cancel", "description": "Отменить действие"},
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info(f"✅ Команды установлены: {len(commands)}")
    except Exception as e:
        logger.error(f"⚠️ Не удалось установить команды: {e}")


# =========================
# Логирование forwarded сообщений — чтобы узнать chat_id приватного канала
# =========================

@router.message(F.forward_from_chat)


# =========================
# HTTP health-check сервер для Render Web Service
# =========================

async def health_handler(request):
    return web.Response(text="OK")


async def start_health_server():
    port = int(os.getenv("PORT", "10000"))
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/healthz", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 Health server started on port {port}")

    # Self-ping каждые 5 минут — чтобы Render free instance не уснул
    async def self_ping():
        try:
            external_url = os.getenv("RENDER_EXTERNAL_URL")
            if not external_url:
                logger.warning("RENDER_EXTERNAL_URL не задан — self-ping отключён")
                return
            ping_url = f"{external_url}/healthz"
            logger.info(f"⏰ Self-ping запущен: {ping_url} каждые 5 минут")
            async with aiohttp.ClientSession() as session:
                while True:
                    await asyncio.sleep(300)  # 5 минут
                    try:
                        async with session.get(ping_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                            logger.info(f"✓ Self-ping {ping_url} → {resp.status}")
                    except Exception as e:
                        logger.warning(f"Self-ping failed: {e}")
        except asyncio.CancelledError:
            return

    asyncio.create_task(self_ping())


async def main():
    await on_startup()
    logger.info("🚀 Бот запускается...")
    if os.getenv("RENDER") == "true":
        # Задержка, чтобы Render успел убить старый процесс и не было TelegramConflictError
        logger.info("⏳ Ждём 30 секунд, чтобы старый polling остановился...")
        await asyncio.sleep(30)
        await start_health_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
