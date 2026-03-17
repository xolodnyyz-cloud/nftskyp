import logging
import re
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
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

# Путь к изображению бота
BOT_PHOTO = FSInputFile("bot_photo.jpg")  # Файл должен лежать в той же папке, что и bot.py

# Курсы конвертации
STARS_TO_RUB = 1.6
RUB_TO_STARS = 0.625

# База данных
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"users": {}, "transactions": []}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Класс для оценки NFT
class NFTParser:
    NFT_PATTERN = r'https?://t\.me/nft/([a-zA-Z0-9_-]+)-(\d+)'
    
    RARE_NFT_DB = {
        "star-1": 10.0, "heart-1": 8.0, "diamond-1": 15.0,
        "alien-42": 5.0, "gold-100": 3.0, "mythic-777": 7.0,
        "durovscap-1": 20.0, "heartlocket-2": 10.0, "plushpepe-3": 8.0,
    }
    
    NAME_MULTIPLIERS = {
        'star': 1.0, 'heart': 1.2, 'diamond': 2.5, 'crown': 1.8,
        'rocket': 2.0, 'alien': 3.0, 'gold': 2.2, 'silver': 1.5,
        'bronze': 1.3, 'mythic': 4.0, 'legendary': 3.5, 'epic': 2.8,
        'rare': 1.8, 'ancient': 3.2, 'space': 2.4, 'rainbow': 2.1,
        'neon': 1.9, 'glitch': 2.6, 'durovscap': 5.0, 'heartlocket': 3.0,
        'plushpepe': 2.5,
    }
    
    @classmethod
    def get_number_multiplier(cls, number_str):
        try:
            number = int(number_str)
            if number < 10:
                return 2.0
            elif number < 100:
                if number % 10 == 0:
                    return 1.5
                elif number % 11 == 0:
                    return 1.8
            elif number < 1000:
                if number % 100 == 0:
                    return 1.8
                elif number % 111 == 0:
                    return 2.2
                elif str(number) == str(number)[::-1]:
                    return 1.6
            elif number < 10000:
                if number % 1000 == 0:
                    return 2.0
                elif number % 1111 == 0:
                    return 3.0
            return 1.0
        except:
            return 1.0
    
    @classmethod
    def parse_nft_link(cls, link):
        match = re.match(cls.NFT_PATTERN, link)
        if match:
            return {
                'name': match.group(1),
                'number': match.group(2),
                'full_link': link
            }
        return None
    
    @classmethod
    def calculate_price(cls, nft_name, nft_number):
        base_price_rub = 500
        
        rare_key = f"{nft_name}-{nft_number}"
        if rare_key in cls.RARE_NFT_DB:
            multiplier = cls.RARE_NFT_DB[rare_key]
        else:
            name_lower = nft_name.lower()
            name_multiplier = 1.0
            
            for key, value in cls.NAME_MULTIPLIERS.items():
                if key in name_lower:
                    name_multiplier = value
                    break
            
            number_multiplier = cls.get_number_multiplier(nft_number)
            multiplier = name_multiplier * number_multiplier
        
        random_factor = random.uniform(0.95, 1.05)
        market_price_rub = round(base_price_rub * multiplier * random_factor, 2)
        our_price_rub = round(market_price_rub * 1.3, 2)
        
        market_price_stars = round(market_price_rub / STARS_TO_RUB, 2)
        our_price_stars = round(our_price_rub / STARS_TO_RUB, 2)
        
        return {
            'market_rub': market_price_rub,
            'market_stars': market_price_stars,
            'our_rub': our_price_rub,
            'our_stars': our_price_stars,
            'multiplier': round(multiplier, 2)
        }

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data.clear()
    context.user_data['state'] = 'main'
    
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
    
    # Отправляем фото с подписью
    try:
        await update.message.reply_photo(
            photo=BOT_PHOTO,
            caption=welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
        # Если фото не отправилось, отправляем только текст
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
    
    # Отправляем фото с инструкцией
    try:
        await query.message.reply_photo(
            photo=BOT_PHOTO,
            caption=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        await query.message.delete()  # Удаляем предыдущее сообщение
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
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
    link = update.message.text.strip()
    nft_data = NFTParser.parse_nft_link(link)
    
    if not nft_data:
        text = (
            "❌ **Неправильный формат ссылки!**\n\n"
            "Формат: `https://t.me/nft/НАЗВАНИЕ-НОМЕР`\n\n"
            "📌 **Примеры:**\n"
            "• `https://t.me/nft/DurovsCap-1`\n"
            "• `https://t.me/nft/HeartLocket-2`\n"
            "• `https://t.me/nft/PlushPepe-3`"
        )
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем фото с ошибкой
        try:
            await update.message.reply_photo(
                photo=BOT_PHOTO,
                caption=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    analyzing_msg = await update.message.reply_text(
        "🔍 **Анализируем ваш NFT...**\nПожалуйста, подождите несколько секунд.",
        parse_mode='Markdown'
    )
    
    await asyncio.sleep(2)
    price_info = NFTParser.calculate_price(nft_data['name'], nft_data['number'])
    
    context.user_data['nft_info'] = {
        'link': nft_data['full_link'],
        'name': nft_data['name'],
        'number': nft_data['number'],
        'market_rub': price_info['market_rub'],
        'market_stars': price_info['market_stars'],
        'our_rub': price_info['our_rub'],
        'our_stars': price_info['our_stars'],
        'multiplier': price_info['multiplier']
    }
    
    await analyzing_msg.delete()
    
    text = (
        "✅ **🔍 Анализ NFT завершён!**\n\n"
        f"📎 **Ваш NFT:** {nft_data['full_link']}\n"
        f"🏷 **Рыночная стоимость:** ~{price_info['market_rub']} ₽ / {price_info['market_stars']} ⭐️\n"
        f"💰 **Наше предложение:** {price_info['our_rub']} ₽ / {price_info['our_stars']} ⭐️ (+30%)\n\n"
        f"✨ **Редкость:** x{price_info['multiplier']}\n\n"
        "**Выберите способ получения оплаты:**"
    )
    
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Карта — Россия (RUB)", callback_data='payment_rub')],
        [InlineKeyboardButton("⭐️ Звезды (Telegram Stars)", callback_data='payment_stars')],
        [InlineKeyboardButton("🔄 Проверить другой NFT", callback_data='check_another')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel_sale')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем фото с результатами
    try:
        await update.message.reply_photo(
            photo=BOT_PHOTO,
            caption=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    context.user_data['state'] = 'awaiting_payment'

async def select_payment_rub(query, context):
    context.user_data['payment_method'] = 'rub'
    context.user_data['payment_name'] = '🇷🇺 Карта — Россия (RUB)'
    context.user_data['state'] = 'awaiting_details'
    
    nft_info = context.user_data.get('nft_info', {})
    
    text = (
        f"💳 **Способ оплаты:** 🇷🇺 Карта — Россия (RUB)\n\n"
        f"📎 **Ваш NFT:** {nft_info.get('link')}\n"
        f"🏷 **Рыночная стоимость:** ~{nft_info.get('market_rub')} ₽\n"
        f"💰 **Наше предложение:** {nft_info.get('our_rub')} ₽ (+30%)\n\n"
        "📝 **Введите ваши реквизиты для получения оплаты:**\n"
        "(Номер карты, телефон и т.д.)"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад к выбору оплаты", callback_data='back_to_payment')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем фото с выбором оплаты
    try:
        await query.message.reply_photo(
            photo=BOT_PHOTO,
            caption=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        await query.message.delete()
    except:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def select_payment_stars(query, context):
    context.user_data['payment_method'] = 'stars'
    context.user_data['payment_name'] = '⭐️ Звезды (Telegram Stars)'
    context.user_data['state'] = 'awaiting_details'
    
    nft_info = context.user_data.get('nft_info', {})
    
    text = (
        f"💳 **Способ оплаты:** ⭐️ Звезды (Telegram Stars)\n\n"
        f"📎 **Ваш NFT:** {nft_info.get('link')}\n"
        f"🏷 **Рыночная стоимость:** ~{nft_info.get('market_stars')} ⭐️\n"
        f"💰 **Наше предложение:** {nft_info.get('our_stars')} ⭐️ (+30%)\n\n"
        "📝 **Введите ваш @username для получения оплаты:**"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад к выбору оплаты", callback_data='back_to_payment')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем фото с выбором оплаты
    try:
        await query.message.reply_photo(
            photo=BOT_PHOTO,
            caption=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        await query.message.delete()
    except:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def back_to_payment(query, context):
    nft_info = context.user_data.get('nft_info', {})
    context.user_data['state'] = 'awaiting_payment'
    
    text = (
        "✅ **🔍 Анализ NFT завершён!**\n\n"
        f"📎 **Ваш NFT:** {nft_info.get('link')}\n"
        f"🏷 **Рыночная стоимость:** ~{nft_info.get('market_rub')} ₽ / {nft_info.get('market_stars')} ⭐️\n"
        f"💰 **Наше предложение:** {nft_info.get('our_rub')} ₽ / {nft_info.get('our_stars')} ⭐️ (+30%)\n\n"
        f"✨ **Редкость:** x{nft_info.get('multiplier')}\n\n"
        "**Выберите способ получения оплаты:**"
    )
    
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Карта — Россия (RUB)", callback_data='payment_rub')],
        [InlineKeyboardButton("⭐️ Звезды (Telegram Stars)", callback_data='payment_stars')],
        [InlineKeyboardButton("🔄 Проверить другой NFT", callback_data='check_another')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel_sale')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем фото с выбором оплаты
    try:
        await query.message.reply_photo(
            photo=BOT_PHOTO,
            caption=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        await query.message.delete()
    except:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        f"🏷 **Рыночная стоимость:** ~{market} {currency}\n"
        f"💰 **Наше предложение:** {amount} {currency}\n\n"
        f"💬 Я предлагаю вам за ваш NFT {nft_info.get('link')} сумму {amount} {currency}\n\n"
        "Если согласны — нажмите **Да**, если нет — **Нет** 👇"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Да", callback_data='confirm_deal')],
        [InlineKeyboardButton("❌ Нет", callback_data='reject_deal')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем фото с предложением
    try:
        await update.message.reply_photo(
            photo=BOT_PHOTO,
            caption=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    context.user_data['state'] = 'awaiting_confirmation'

async def confirm_deal(query, context):
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
        f"💵 **Сумма выплаты:** {amount} {currency}\n"
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
    
    # Отправляем фото с подтверждением
    try:
        await query.message.reply_photo(
            photo=BOT_PHOTO,
            caption=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        await query.message.delete()
    except:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def gift_sent(query, context):
    """Обработчик кнопки 'Подарок передан'"""
    nft_info = context.user_data.get('nft_info', {})
    payment_method = context.user_data.get('payment_method')
    payment_name = context.user_data.get('payment_name')
    
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
        f"💵 **Сумма выплаты:** {amount} {currency}\n\n"
        f"Ожидайте поступления оплаты в течение 5–15 минут.\n"
        f"Если возникнут вопросы, обращайтесь к @{MANAGER_USERNAME}"
    )
    
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем фото с подтверждением
    try:
        await query.message.reply_photo(
            photo=BOT_PHOTO,
            caption=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        await query.message.delete()
    except:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # Уведомление админам о том, что подарок передан
    for admin_id in ADMIN_IDS:
        try:
            admin_text = (
                f"📦 **Подарок передан!**\n\n"
                f"👤 **Пользователь:** @{query.from_user.username}\n"
                f"🆔 **ID:** {query.from_user.id}\n"
                f"📎 **NFT:** {nft_info.get('link')}\n"
                f"💰 **Сумма:** {amount} {currency}\n"
                f"⏰ **Время:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
            await context.bot.send_message(admin_id, admin_text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    context.user_data.clear()

async def reject_deal(query, context):
    text = "❌ Сделка отменена. Возвращаемся в главное меню."
    
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем фото с отменой
    try:
        await query.message.reply_photo(
            photo=BOT_PHOTO,
            caption=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        await query.message.delete()
    except:
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    context.user_data.clear()

async def check_another(query, context):
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
    
    # Отправляем фото с инструкцией
    try:
        await query.message.reply_photo(
            photo=BOT_PHOTO,
            caption=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        await query.message.delete()
    except:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def cancel_sale(query, context):
    text = "❌ Продажа отменена. Возвращаемся в главное меню."
    
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем фото с отменой
    try:
        await query.message.reply_photo(
            photo=BOT_PHOTO,
            caption=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        await query.message.delete()
    except:
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    context.user_data.clear()

async def show_instructions(query, context):
    instructions = (
        "🤝 **Как проводится сделка:**\n\n"
        "1. Вы присылаете ссылку на NFT-подарок\n"
        "2. Бот считает рыночную цену по параметрам: модель, фон, узор\n"
        "3. Вы выбираете способ оплаты\n"
        "4. Бот озвучивает свою сумму в вашей валюте\n\n"
        "Пример: Я предлагаю вам за ваш NFT https://t.me/nft/HeartLocket-2  — 281.511 Рублей\n"
        "Если согласны — нажмите Да, если нет — Нет\n\n"
        "5. При согласии — отправьте NFT менеджеру @nftsbuyer\n"
        "6. Менеджер проверяет подарок и переводит оплату на ваши реквизиты\n\n"
        "⚡️ Среднее время сделки: 5–15 минут"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем фото с инструкцией
    try:
        await query.message.reply_photo(
            photo=BOT_PHOTO,
            caption=instructions,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        await query.message.delete()
    except:
        await query.edit_message_text(instructions, reply_markup=reply_markup, parse_mode='Markdown')

async def show_support(query, context):
    support_text = (
        "🆘 **Поддержка**\n\n"
        f"По всем вопросам обращайтесь к менеджеру @{MANAGER_USERNAME}\n\n"
        "⏰ **Время работы:** 24/7\n\n"
        "Среднее время ответа: 5-10 минут"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем фото с поддержкой
    try:
        await query.message.reply_photo(
            photo=BOT_PHOTO,
            caption=support_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        await query.message.delete()
    except:
        await query.edit_message_text(support_text, reply_markup=reply_markup, parse_mode='Markdown')

async def back_to_main(query, context):
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
    
    # Отправляем фото с приветствием
    try:
        await query.message.reply_photo(
            photo=BOT_PHOTO,
            caption=welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        await query.message.delete()
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
        await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

def main():
    print("=" * 50)
    print("ЗАПУСК БОТА ДЛЯ СКУПКИ NFT С ФОТО")
    print("=" * 50)
    
    try:
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
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        print(f"❌ Ошибка при запуске: {e}")

if __name__ == '__main__':
    main()
