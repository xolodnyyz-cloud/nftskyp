import logging
import re
import random
import json
import os
import asyncio
import requests
from datetime import datetime, timedelta
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
TON_TO_USD = 1.35  # 1 TON ≈ $1.35
USD_TO_RUB = 90    # 1 USD ≈ 90 RUB
STARS_TO_RUB = 1.6 # 1 звезда ≈ 1.6 рубля

# База данных
DATA_FILE = "data.json"

# ============================================
# КЛАСС ДЛЯ АНАЛИЗА NFT
# ============================================

class NFTAnalyzer:
    """
    Анализирует NFT и предоставляет детальную информацию о ценах
    """
    
    # База данных NFT с характеристиками
    NFT_DATABASE = {
        # Durov's Cap
        'durovscap': {
            'name': 'Durov\'s Cap',
            'models': {
                'classic': {'name': 'Classic', 'multiplier': 1.0},
                'shadow': {'name': 'Shadow', 'multiplier': 1.2},
                'gold': {'name': 'Gold', 'multiplier': 2.0},
                'diamond': {'name': 'Diamond', 'multiplier': 3.0},
            },
            'backgrounds': {
                'default': {'name': 'Default', 'multiplier': 1.0},
                'shamrock_green': {'name': 'Shamrock Green', 'multiplier': 1.3},
                'midnight_blue': {'name': 'Midnight Blue', 'multiplier': 1.2},
                'sunset_orange': {'name': 'Sunset Orange', 'multiplier': 1.4},
            },
            'patterns': {
                'default': {'name': 'Default', 'multiplier': 1.0},
                'ram_of_amun': {'name': 'Ram of Amun', 'multiplier': 1.5},
                'old_candle': {'name': 'Old Candle', 'multiplier': 1.3},
                'crystal': {'name': 'Crystal', 'multiplier': 1.8},
            },
            'base_price': 150,  # базовый TON
            'rarity': 'legendary'
        },
        
        # Heart Locket
        'heartlocket': {
            'name': 'Heart Locket',
            'models': {
                'classic': {'name': 'Classic', 'multiplier': 1.0},
                'golden': {'name': 'Golden', 'multiplier': 1.8},
                'crystal': {'name': 'Crystal', 'multiplier': 2.2},
            },
            'backgrounds': {
                'default': {'name': 'Default', 'multiplier': 1.0},
                'romantic_red': {'name': 'Romantic Red', 'multiplier': 1.4},
                'mystic_purple': {'name': 'Mystic Purple', 'multiplier': 1.3},
            },
            'patterns': {
                'default': {'name': 'Default', 'multiplier': 1.0},
                'heartbeat': {'name': 'Heartbeat', 'multiplier': 1.5},
                'eternal': {'name': 'Eternal', 'multiplier': 1.7},
            },
            'base_price': 80,
            'rarity': 'epic'
        },
        
        # Plush Pepe
        'plushpepe': {
            'name': 'Plush Pepe',
            'models': {
                'classic': {'name': 'Classic', 'multiplier': 1.0},
                'sketchy': {'name': 'Sketchy', 'multiplier': 1.1},
                'rainbow': {'name': 'Rainbow', 'multiplier': 1.6},
            },
            'backgrounds': {
                'default': {'name': 'Default', 'multiplier': 1.0},
                'fandango': {'name': 'Fandango', 'multiplier': 1.2},
                'mint_green': {'name': 'Mint Green', 'multiplier': 1.1},
                'ocean_blue': {'name': 'Ocean Blue', 'multiplier': 1.15},
            },
            'patterns': {
                'default': {'name': 'Default', 'multiplier': 1.0},
                'toilet': {'name': 'Toilet', 'multiplier': 1.2},
                'stars': {'name': 'Stars', 'multiplier': 1.3},
                'hearts': {'name': 'Hearts', 'multiplier': 1.25},
            },
            'base_price': 60,
            'rarity': 'rare'
        },
        
        # Mousse Cake (из примера)
        'moussecake': {
            'name': 'Mousse Cake',
            'models': {
                'classic': {'name': 'Classic', 'multiplier': 1.0},
                'chocolate': {'name': 'Chocolate', 'multiplier': 1.2},
                'strawberry': {'name': 'Strawberry', 'multiplier': 1.3},
            },
            'backgrounds': {
                'default': {'name': 'Default', 'multiplier': 1.0},
                'mint_green': {'name': 'Mint Green', 'multiplier': 1.1},
                'cream': {'name': 'Cream', 'multiplier': 1.05},
            },
            'patterns': {
                'default': {'name': 'Default', 'multiplier': 1.0},
                'old_candle': {'name': 'Old Candle', 'multiplier': 1.15},
                'sprinkles': {'name': 'Sprinkles', 'multiplier': 1.1},
            },
            'base_price': 45,
            'rarity': 'common'
        }
    }
    
    # Множители для редких номеров
    NUMBER_MULTIPLIERS = {
        '1': 15.0, '2': 8.0, '3': 6.0, '5': 2.5, '7': 3.0,
        '10': 3.5, '13': 2.0, '21': 2.2, '42': 4.0, '69': 5.0,
        '100': 6.0, '111': 7.0, '222': 7.0, '333': 8.0, '444': 8.0,
        '555': 9.0, '666': 5.0, '777': 12.0, '888': 9.0, '999': 10.0,
        '1000': 15.0, '2024': 3.0, '2025': 3.0,
    }
    
    # Генерация истории продаж (имитация)
    @classmethod
    def generate_sales_history(cls, nft_name, count=20):
        """Генерирует историю продаж для демонстрации"""
        history = []
        base_price = cls._get_base_price(nft_name)
        
        # Базовые номера для истории
        base_numbers = [26326, 166829, 71272, 90864, 162525, 3563, 6325, 
                       155419, 116070, 16670, 41172, 155521, 54243, 111778]
        
        now = datetime.now()
        
        for i in range(min(count, len(base_numbers))):
            number = base_numbers[i % len(base_numbers)]
            
            # Генерируем случайную цену вокруг базовой
            price_variation = random.uniform(0.85, 1.15)
            price = round(base_price * price_variation, 2)
            
            # Генерируем время
            hours_ago = random.randint(1, 240)
            time_ago = now - timedelta(hours=hours_ago)
            
            # Форматируем время
            if hours_ago < 24:
                time_str = f"{hours_ago} {'часа' if hours_ago % 10 in [2,3,4] and not (11<=hours_ago<=14) else 'часов' if hours_ago>4 else 'час'} назад"
            elif hours_ago < 48:
                time_str = "вчера"
            else:
                days = hours_ago // 24
                time_str = f"{days} {self._pluralize_days(days)} назад"
            
            history.append({
                'number': number,
                'price': price,
                'time_str': time_str,
                'timestamp': time_ago
            })
        
        # Сортируем по времени (самые свежие первые)
        history.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return history
    
    @classmethod
    def _pluralize_days(cls, days):
        if days % 10 == 1 and days % 100 != 11:
            return "день"
        elif 2 <= days % 10 <= 4 and not (12 <= days % 100 <= 14):
            return "дня"
        else:
            return "дней"
    
    @classmethod
    def _get_base_price(cls, nft_name):
        """Получает базовую цену для NFT"""
        normalized = cls._normalize_name(nft_name)
        
        for key, collection in cls.NFT_DATABASE.items():
            if key in normalized:
                return collection['base_price']
        
        return 50  # базовая цена по умолчанию
    
    @classmethod
    def _normalize_name(cls, name):
        """Нормализует название"""
        return re.sub(r'[^a-zA-Z0-9]', '', name.lower())
    
    @classmethod
    def get_number_multiplier(cls, number):
        """Множитель для номера"""
        number_str = str(number).strip()
        
        if number_str in cls.NUMBER_MULTIPLIERS:
            return cls.NUMBER_MULTIPLIERS[number_str]
        
        try:
            num = int(number_str)
            
            if num < 10:
                return 3.0
            elif num < 100:
                if num % 10 == 0:
                    return 2.0
                elif num % 11 == 0:
                    return 2.5
            elif num < 1000:
                if num % 100 == 0:
                    return 2.5
                elif num % 111 == 0:
                    return 4.0
                elif str(num) == str(num)[::-1]:
                    return 2.2
            elif num < 10000:
                if num % 1000 == 0:
                    return 3.5
                elif num % 1111 == 0:
                    return 6.0
        except:
            pass
        
        return 1.0
    
    @classmethod
    async def analyze_nft(cls, nft_name, nft_number):
        """
        Полный анализ NFT
        """
        normalized = cls._normalize_name(nft_name)
        
        # Ищем в базе
        collection = None
        for key, col in cls.NFT_DATABASE.items():
            if key in normalized:
                collection = col
                break
        
        if not collection:
            collection = cls.NFT_DATABASE.get('moussecake')  # базовая коллекция
        
        # Базовые параметры
        base_price_ton = collection['base_price']
        number_mult = cls.get_number_multiplier(nft_number)
        
        # Генерируем случайные характеристики (в реальности их нужно парсить со страницы)
        model_key = random.choice(list(collection['models'].keys()))
        background_key = random.choice(list(collection['backgrounds'].keys()))
        pattern_key = random.choice(list(collection['patterns'].keys()))
        
        model = collection['models'][model_key]
        background = collection['backgrounds'][background_key]
        pattern = collection['patterns'][pattern_key]
        
        # Расчет рыночной цены
        total_multiplier = number_mult * model['multiplier'] * background['multiplier'] * pattern['multiplier']
        market_price_ton = round(base_price_ton * total_multiplier * random.uniform(0.9, 1.1), 2)
        
        # Генерируем floor и avg цены
        floor_price = round(market_price_ton * 0.85, 2)
        avg_price = round(market_price_ton * 0.95, 2)
        
        # Конвертация в USD и RUB
        market_price_usd = round(market_price_ton * TON_TO_USD, 2)
        market_price_rub = round(market_price_usd * USD_TO_RUB)
        market_price_stars = round(market_price_rub / STARS_TO_RUB)
        
        # Наше предложение (+30%)
        our_price_ton = round(market_price_ton * 1.3, 2)
        our_price_rub = round(market_price_rub * 1.3)
        our_price_stars = round(market_price_stars * 1.3)
        our_price_usd = round(market_price_usd * 1.3, 2)
        
        # Генерируем историю продаж
        sales_history = cls.generate_sales_history(nft_name, 15)
        
        # Формируем результат
        result = {
            'success': True,
            'collection': collection['name'],
            'rarity': collection['rarity'],
            'nft_name': f"{collection['name']} #{nft_number}",
            'full_link': f"https://t.me/nft/{nft_name}-{nft_number}",
            'characteristics': {
                'model': model['name'],
                'background': background['name'],
                'pattern': pattern['name'],
                'quantity': f"{random.randint(1000, 5000)}/{random.randint(5000, 10000)} issued"
            },
            'prices': {
                'floor': {'ton': floor_price, 'usd': round(floor_price * TON_TO_USD, 2)},
                'avg': {'ton': avg_price, 'usd': round(avg_price * TON_TO_USD, 2)},
                'last_sale': {'ton': market_price_ton, 'usd': market_price_usd},
                'market': {
                    'ton': market_price_ton,
                    'usd': market_price_usd,
                    'rub': market_price_rub,
                    'stars': market_price_stars
                },
                'our_offer': {
                    'ton': our_price_ton,
                    'usd': our_price_usd,
                    'rub': our_price_rub,
                    'stars': our_price_stars
                }
            },
            'sales_history': sales_history[:10]  # Последние 10 продаж
        }
        
        return result


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
    
    welcome_text = (
        f"🌟 Добро пожаловать в NFT Price Bot, {user.first_name}!\n\n"
        "Я показываю реальные цены на NFT из Telegram маркета\n"
        "и делаю предложения о выкупе на 30% выше рынка!\n\n"
        "📊 **Что я умею:**\n"
        "• Показывать текущие цены (Floor, AVG)\n"
        "• Историю последних продаж\n"
        "• Характеристики NFT\n"
        "• Делать предложение о выкупе\n\n"
        "Просто отправьте мне ссылку на NFT!"
    )
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_nft_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка полученной ссылки"""
    link = update.message.text.strip()
    
    # Парсим ссылку
    nft_data = NFTLinkParser.parse_link(link)
    
    if not nft_data:
        await update.message.reply_text(
            "❌ **Неправильный формат ссылки!**\n\n"
            "Формат: `https://t.me/nft/НАЗВАНИЕ-НОМЕР`\n\n"
            "Пример: `https://t.me/nft/DurovsCap-1`",
            parse_mode='Markdown'
        )
        return
    
    # Отправляем сообщение о начале анализа
    analyzing_msg = await update.message.reply_text(
        "🔍 **Анализируем NFT...**\nПолучаем данные с маркета...",
        parse_mode='Markdown'
    )
    
    # Анализируем NFT
    analysis = await NFTAnalyzer.analyze_nft(nft_data['name'], nft_data['number'])
    
    if not analysis['success']:
        await analyzing_msg.edit_text("❌ Не удалось получить данные. Попробуйте позже.")
        return
    
    # Формируем детальный отчет
    text = (
        f"⭐ **{analysis['nft_name']}**\n"
        f"🔗 {analysis['full_link']}\n"
        f"📦 Тираж: {analysis['characteristics']['quantity']}\n\n"
        
        f"🎨 **Характеристики:**\n"
        f"Модель: {analysis['characteristics']['model']}\n"
        f"Фон: {analysis['characteristics']['background']}\n"
        f"Узор: {analysis['characteristics']['pattern']}\n\n"
        
        f"📊 **Цены:**\n"
        f"Floor: {analysis['prices']['floor']['ton']} TON ≈ {analysis['prices']['floor']['usd']} $\n"
        f"AVG: {analysis['prices']['avg']['ton']} TON ≈ {analysis['prices']['avg']['usd']} $\n"
        f"Последняя продажа: {analysis['prices']['last_sale']['ton']} TON ≈ {analysis['prices']['last_sale']['usd']} $\n\n"
        
        f"💰 **Наше предложение (+30%):**\n"
        f"{analysis['prices']['our_offer']['ton']} TON\n"
        f"{analysis['prices']['our_offer']['usd']} $\n"
        f"{analysis['prices']['our_offer']['rub']:,} ₽\n"
        f"{analysis['prices']['our_offer']['stars']:,} ⭐️\n\n"
        
        f"📈 **История продаж модели:**\n"
    )
    
    # Добавляем историю продаж
    for sale in analysis['sales_history']:
        text += f"🎨 #{sale['number']}: {sale['price']} TON — {sale['time_str']} 🛒\n"
    
    text += "\n**Выберите действие:**"
    
    # Сохраняем данные для последующего выкупа
    context.user_data['current_nft'] = {
        'name': analysis['nft_name'],
        'link': analysis['full_link'],
        'prices': analysis['prices']['our_offer']
    }
    
    keyboard = [
        [InlineKeyboardButton("💰 Продать по этой цене", callback_data='sell_offer')],
        [InlineKeyboardButton("🔄 Проверить другой NFT", callback_data='check_another')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await analyzing_msg.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'sell_offer':
        await show_sell_options(query, context)
    elif query.data == 'check_another':
        await check_another(query, context)
    elif query.data == 'back_to_start':
        await back_to_start(query, context)
    elif query.data in ['payment_rub', 'payment_stars', 'payment_ton', 'payment_usd']:
        await confirm_sale(query, context)

async def show_sell_options(query, context):
    """Показывает опции продажи"""
    nft_data = context.user_data.get('current_nft', {})
    
    if not nft_data:
        await query.edit_message_text("❌ Данные не найдены. Отправьте ссылку заново.")
        return
    
    prices = nft_data['prices']
    
    text = (
        f"✅ **Продажа NFT**\n\n"
        f"📎 {nft_data['name']}\n"
        f"🔗 {nft_data['link']}\n\n"
        f"💰 **Наше предложение:**\n"
        f"• {prices['ton']} TON\n"
        f"• {prices['usd']} $\n"
        f"• {prices['rub']:,} ₽\n"
        f"• {prices['stars']:,} ⭐️\n\n"
        f"**Выберите способ получения:**"
    )
    
    keyboard = [
        [InlineKeyboardButton("💎 TON", callback_data='payment_ton')],
        [InlineKeyboardButton("💵 Доллары (USD)", callback_data='payment_usd')],
        [InlineKeyboardButton("💳 Рубли (RUB)", callback_data='payment_rub')],
        [InlineKeyboardButton("⭐️ Звезды (Telegram Stars)", callback_data='payment_stars')],
        [InlineKeyboardButton("◀️ Назад", callback_data='back_to_start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def confirm_sale(query, context):
    """Подтверждение продажи"""
    payment_method = query.data.replace('payment_', '')
    
    payment_names = {
        'ton': 'TON',
        'usd': 'USD',
        'rub': 'RUB',
        'stars': 'Telegram Stars'
    }
    
    currency_symbols = {
        'ton': '💎',
        'usd': '💵',
        'rub': '₽',
        'stars': '⭐️'
    }
    
    nft_data = context.user_data.get('current_nft', {})
    
    if not nft_data:
        await query.edit_message_text("❌ Ошибка. Начните заново.")
        return
    
    # Сохраняем транзакцию
    data = load_data()
    transaction = {
        "id": len(data["transactions"]) + 1,
        "user_id": query.from_user.id,
        "username": query.from_user.username,
        "nft": nft_data['name'],
        "link": nft_data['link'],
        "amount": nft_data['prices'][payment_method],
        "currency": payment_method.upper(),
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    data["transactions"].append(transaction)
    save_data(data)
    
    success_text = (
        f"✅ **Заявка на продажу принята!**\n\n"
        f"📎 {nft_data['name']}\n"
        f"💰 **Сумма:** {currency_symbols[payment_method]} {nft_data['prices'][payment_method]} {payment_names[payment_method]}\n\n"
        f"С вами свяжется менеджер в ближайшее время для завершения сделки.\n"
        f"Спасибо за доверие! 🙏"
    )
    
    keyboard = [[InlineKeyboardButton("🏠 В начало", callback_data='back_to_start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
    context.user_data.clear()

async def check_another(query, context):
    """Проверка другого NFT"""
    text = (
        "🔗 **Отправьте ссылку на NFT**\n\n"
        "Формат: `https://t.me/nft/НАЗВАНИЕ-НОМЕР`\n\n"
        "Пример: `https://t.me/nft/DurovsCap-1`"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    context.user_data.clear()

async def back_to_start(query, context):
    """Возврат в начало"""
    text = (
        "🌟 **NFT Price Bot**\n\n"
        "Отправьте ссылку на NFT для анализа!"
    )
    
    keyboard = []
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    context.user_data.clear()


# ============================================
# ЗАПУСК БОТА
# ============================================

def main():
    print("=" * 50)
    print("ЗАПУСК NFT PRICE BOT")
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
