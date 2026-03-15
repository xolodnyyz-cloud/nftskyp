import logging
import re
import json
import os
import asyncio
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

TOKEN = "8527173088:AAFENDpLWuQmRJe9ioRN4a1IbcnyqGgOkag"
ADMIN_IDS = []  # Добавьте свой Telegram ID

# Курсы конвертации
STARS_TO_RUB = 1.6
TON_TO_RUB = 90

# База данных
DATA_FILE = "data.json"

# ============================================
# КЛАСС ДЛЯ ПАРСИНГА @PriceNFTbot
# ============================================

class PriceNFTParser:
    """
    Парсер для получения цен с @PriceNFTbot
    В реальности нужно использовать Telethon для парсинга сообщений
    """
    
    # Кэш для результатов
    _cache = {}
    _cache_time = {}
    CACHE_TTL = 300  # 5 минут
    
    @classmethod
    async def get_nft_price(cls, nft_name, nft_number):
        """
        Получает цену NFT имитируя @PriceNFTbot
        """
        cache_key = f"{nft_name.lower()}-{nft_number}"
        
        # Проверяем кэш
        if cache_key in cls._cache:
            cache_age = (datetime.now() - cls._cache_time.get(cache_key, datetime.min)).seconds
            if cache_age < cls.CACHE_TTL:
                return cls._cache[cache_key]
        
        # В реальности здесь должен быть код для парсинга @PriceNFTbot
        # Сейчас используем имитацию на основе данных из примера
        
        # Пример данных как в @PriceNFTbot
        price_data = {
            'success': True,
            'nft_name': f"{nft_name} #{nft_number}",
            'full_link': f"https://t.me/nft/{nft_name}-{nft_number}",
            'characteristics': {
                'model': 'Mousse Cake',
                'background': 'Mint Green',
                'pattern': 'Old Candle',
                'quantity': '3243 шт.'
            },
            'prices': {
                'floor': {'ton': 4.59, 'usd': 6.2},
                'avg': {'ton': 5.04, 'usd': 6.8},
                'last_sale': {'ton': 5.00, 'usd': 6.7}
            },
            'sales_history': [
                {'number': 26326, 'price': 5.00, 'time': '2 часа назад'},
                {'number': 166829, 'price': 5.02, 'time': '4 часа назад'},
                {'number': 71272, 'price': 4.97, 'time': '6 часов назад'},
                {'number': 90864, 'price': 5.41, 'time': '7 часов назад'},
                {'number': 162525, 'price': 5.20, 'time': '8 часов назад'},
            ]
        }
        
        # Сохраняем в кэш
        cls._cache[cache_key] = price_data
        cls._cache_time[cache_key] = datetime.now()
        
        return price_data


# ============================================
# КЛАСС ДЛЯ ПАРСИНГА ССЫЛОК
# ============================================

class NFTLinkParser:
    NFT_PATTERN = r'https?://t\.me/nft/([a-zA-Z0-9_-]+)-(\d+)'
    
    @classmethod
    def parse_link(cls, link):
        """Парсит ссылку на NFT"""
        match = re.match(cls.NFT_PATTERN, link)
        if not match:
            return None
        
        name = match.group(1)
        number = match.group(2)
        
        return {
            'name': name,
            'number': number,
            'full_link': link
        }


# ============================================
# РАБОТА С БАЗОЙ ДАННЫХ
# ============================================

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"users": {}, "transactions": []}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
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
        f"🌟 Добро пожаловать в Автоматическую Скупку NFT-подарков, {user.first_name}!\n\n"
        "Мы используем данные с @PriceNFTbot для оценки ваших NFT\n\n"
        "✅ Оценка на 30% выше рынка\n"
        "⚡ Мгновенные выплаты\n"
        "🔒 Полная безопасность\n\n"
        "Выберите действие:"
    )
    
    keyboard = [
        [InlineKeyboardButton("💰 Продать NFT", callback_data='sell')],
        [InlineKeyboardButton("📋 Как проходит сделка?", callback_data='how_it_works')],
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
    elif query.data in ['payment_rub', 'payment_stars']:
        await select_payment_method(query, context)
    elif query.data == 'confirm_sale':
        await confirm_sale(query, context)
    elif query.data == 'cancel_sale':
        await cancel_sale(query, context)
    elif query.data == 'back_to_main':
        await back_to_main(query, context)
    elif query.data == 'check_another':
        await check_another(query, context)

async def start_selling(query, context):
    """Начало процесса продажи"""
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

async def handle_nft_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка полученной ссылки"""
    if context.user_data.get('state') != 'waiting_for_link':
        return
    
    link = update.message.text.strip()
    
    # Парсим ссылку
    nft_data = NFTLinkParser.parse_link(link)
    
    if not nft_data:
        text = (
            "❌ **Неправильный формат ссылки!**\n\n"
            "Формат: `https://t.me/nft/НАЗВАНИЕ-НОМЕР`\n\n"
            "Пример: `https://t.me/nft/DurovsCap-1`"
        )
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    # Отправляем сообщение о начале анализа
    analyzing_msg = await update.message.reply_text(
        "🔍 **Запрашиваем данные у @PriceNFTbot...**\nПожалуйста, подождите...",
        parse_mode='Markdown'
    )
    
    # Получаем цену (имитация парсинга @PriceNFTbot)
    price_data = await PriceNFTParser.get_nft_price(nft_data['name'], nft_data['number'])
    
    # Удаляем сообщение об анализе
    await analyzing_msg.delete()
    
    # Рассчитываем наше предложение (+30%)
    last_sale_ton = price_data['prices']['last_sale']['ton']
    our_price_ton = round(last_sale_ton * 1.3, 2)
    our_price_rub = round(our_price_ton * TON_TO_RUB)
    our_price_stars = round(our_price_rub / STARS_TO_RUB)
    
    # Сохраняем данные
    context.user_data['nft_info'] = {
        'link': nft_data['full_link'],
        'name': price_data['nft_name'],
        'market_price': last_sale_ton,
        'our_price_ton': our_price_ton,
        'our_price_rub': our_price_rub,
        'our_price_stars': our_price_stars
    }
    
    # Формируем сообщение с результатом как в @PriceNFTbot
    text = (
        f"⭐ **{price_data['nft_name']}**\n"
        f"🔗 {price_data['full_link']}\n"
        f"📦 Тираж: {price_data['characteristics']['quantity']}\n\n"
        
        f"🎨 **Характеристики:**\n"
        f"Модель: {price_data['characteristics']['model']}\n"
        f"Фон: {price_data['characteristics']['background']}\n"
        f"Узор: {price_data['characteristics']['pattern']}\n\n"
        
        f"📊 **Цены:**\n"
        f"Floor: {price_data['prices']['floor']['ton']} TON ≈ {price_data['prices']['floor']['usd']} $\n"
        f"AVG: {price_data['prices']['avg']['ton']} TON ≈ {price_data['prices']['avg']['usd']} $\n"
        f"Последняя продажа: {price_data['prices']['last_sale']['ton']} TON ≈ {price_data['prices']['last_sale']['usd']} $\n\n"
        
        f"💰 **Наше предложение (+30%):** {our_price_ton} TON\n"
        f"{our_price_rub:,} ₽ / {our_price_stars:,} ⭐️\n\n"
        
        f"📈 **История продаж модели:**\n"
    )
    
    # Добавляем историю продаж
    for sale in price_data['sales_history']:
        text += f"🎨 #{sale['number']}: {sale['price']} TON — {sale['time']} 🛒\n"
    
    text += "\n**Выберите способ получения оплаты:**"
    
    keyboard = [
        [InlineKeyboardButton("💵 Рубли (₽)", callback_data='payment_rub')],
        [InlineKeyboardButton("⭐️ Звезды (Telegram Stars)", callback_data='payment_stars')],
        [InlineKeyboardButton("🔄 Проверить другой NFT", callback_data='check_another')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel_sale')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    context.user_data['state'] = 'awaiting_payment'

async def select_payment_method(query, context):
    """Выбор способа оплаты"""
    payment_method = 'rub' if query.data == 'payment_rub' else 'stars'
    context.user_data['payment_method'] = payment_method
    
    nft_info = context.user_data.get('nft_info', {})
    
    if payment_method == 'rub':
        amount = nft_info.get('our_price_rub', 0)
        currency = '₽'
        currency_name = 'рублях'
    else:
        amount = nft_info.get('our_price_stars', 0)
        currency = '⭐️'
        currency_name = 'звездах'
    
    text = (
        f"✅ **Вы выбрали оплату в {currency_name}**\n\n"
        f"💰 **Сумма к выплате:** {amount:,} {currency}\n\n"
        "Подтвердите продажу:"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить продажу", callback_data='confirm_sale')],
        [InlineKeyboardButton("◀️ Назад к выбору", callback_data='back_to_payment')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel_sale')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def confirm_sale(query, context):
    """Подтверждение продажи"""
    nft_info = context.user_data.get('nft_info', {})
    payment_method = context.user_data.get('payment_method', 'rub')
    
    if payment_method == 'rub':
        amount = nft_info.get('our_price_rub', 0)
        currency = '₽'
        currency_name = 'рубли'
    else:
        amount = nft_info.get('our_price_stars', 0)
        currency = '⭐️'
        currency_name = 'звезды'
    
    # Сохраняем транзакцию
    data = load_data()
    transaction = {
        "id": len(data["transactions"]) + 1,
        "user_id": query.from_user.id,
        "username": query.from_user.username,
        "nft": nft_info.get('name'),
        "link": nft_info.get('link'),
        "amount": amount,
        "currency": currency,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    data["transactions"].append(transaction)
    save_data(data)
    
    success_text = (
        "✅ **Заявка на продажу принята!**\n\n"
        f"💰 **Сумма:** {amount:,} {currency}\n"
        f"💳 **Способ оплаты:** {currency_name}\n\n"
        "С вами свяжется менеджер в ближайшее время.\n"
        "Спасибо за доверие! 🙏"
    )
    
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
    context.user_data.clear()

async def check_another(query, context):
    """Проверка другого NFT"""
    context.user_data['state'] = 'waiting_for_link'
    
    text = (
        "🔗 **Отправьте ссылку на другой NFT-подарок**\n\n"
        "Формат: `https://t.me/nft/НАЗВАНИЕ-НОМЕР`\n\n"
        "📌 **Пример:** `https://t.me/nft/DurovsCap-1`"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def cancel_sale(query, context):
    """Отмена продажи"""
    text = "❌ Продажа отменена"
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)
    context.user_data.clear()

async def show_instructions(query, context):
    """Инструкция"""
    text = (
        "📋 **Как проходит сделка:**\n\n"
        "1️⃣ Отправьте ссылку на NFT\n"
        "2️⃣ Бот получает данные с @PriceNFTbot\n"
        "3️⃣ Вы получаете предложение +30%\n"
        "4️⃣ Выбираете способ оплаты\n"
        "5️⃣ Менеджер связывается с вами\n"
        "6️⃣ Мгновенная выплата"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_support(query, context):
    """Поддержка"""
    text = "🆘 **Поддержка:** @support_username"
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def back_to_main(query, context):
    """Возврат в главное меню"""
    context.user_data.clear()
    
    text = "🏠 **Главное меню**"
    
    keyboard = [
        [InlineKeyboardButton("💰 Продать NFT", callback_data='sell')],
        [InlineKeyboardButton("📋 Как проходит сделка?", callback_data='how_it_works')],
        [InlineKeyboardButton("🆘 Поддержка", callback_data='support')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


# ============================================
# ЗАПУСК БОТА
# ============================================

def main():
    print("=" * 50)
    print("ЗАПУСК БОТА ДЛЯ СКУПКИ NFT")
    print("=" * 50)
    
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Регистрация обработчиков
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_nft_link))
        
        print("✅ Бот успешно инициализирован!")
        print("🚀 Запуск polling...")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    main()
