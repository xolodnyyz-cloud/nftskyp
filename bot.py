import logging
import re
import random
import json
import os
import asyncio
import requests
from bs4 import BeautifulSoup
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
STARS_TO_RUB = 1.6  # 1 звезда = 1.6 рубля
RUB_TO_STARS = 0.625

# База данных
DATA_FILE = "data.json"

# ============================================
# КЛАСС ДЛЯ РАБОТЫ С FRAGMENT.COM
# ============================================

class FragmentParser:
    """
    Парсер для получения реальных цен NFT с Fragment.com
    """
    
    # База известных коллекций
    KNOWN_COLLECTIONS = {
        'durovscap': {
            'name': 'Durov’s Cap', 
            'base_price': 150, 
            'rarity': 'legendary',
            'description': 'Легендарная кепка Дурова'
        },
        'heartlocket': {
            'name': 'Heart Locket', 
            'base_price': 80, 
            'rarity': 'epic',
            'description': 'Медальон в форме сердца'
        },
        'plushpepe': {
            'name': 'Plush Pepe', 
            'base_price': 60, 
            'rarity': 'rare',
            'description': 'Мягкий Пепе'
        },
    }
    
    # Множители для редких номеров
    NUMBER_MULTIPLIERS = {
        '1': 10.0,   # Первый выпуск
        '2': 5.0,    # Второй
        '3': 4.0,    # Третий
        '7': 1.5,    
        '10': 2.0,   
        '13': 1.2,   
        '21': 1.3,   
        '42': 2.5,   
        '69': 3.0,   
        '100': 3.5,  
        '111': 4.0,  
        '222': 4.0,
        '333': 4.5,
        '444': 4.5,
        '555': 5.0,
        '666': 3.0,
        '777': 7.0,
        '888': 5.0,
        '999': 6.0,
        '1000': 8.0,
    }
    
    # Кэш для результатов
    _cache = {}
    _cache_time = {}
    CACHE_TTL = 3600  # 1 час

    @classmethod
    async def get_nft_price(cls, nft_name, nft_number):
        """
        Получает цену NFT с Fragment.com
        """
        cache_key = f"{nft_name.lower()}-{nft_number}"
        
        # Проверяем кэш
        if cache_key in cls._cache:
            cache_age = (datetime.now() - cls._cache_time.get(cache_key, datetime.min)).seconds
            if cache_age < cls.CACHE_TTL:
                return cls._cache[cache_key]
        
        # Пытаемся получить реальные данные
        price_data = await cls._fetch_from_fragment(nft_name, nft_number)
        
        # Если не получили, используем алгоритмический расчет
        if not price_data['success']:
            price_data = cls._calculate_price(nft_name, nft_number)
        
        # Сохраняем в кэш
        cls._cache[cache_key] = price_data
        cls._cache_time[cache_key] = datetime.now()
        
        return price_data

    @classmethod
    async def _fetch_from_fragment(cls, nft_name, nft_number):
        """
        Парсит данные с Fragment.com
        """
        try:
            # Приводим название к формату для поиска
            search_name = cls._normalize_name(nft_name)
            
            # Формируем URL для поиска
            search_url = f"https://fragment.com/nfts?query={search_name}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(
                search_url, 
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Ищем цены похожих NFT
                prices = []
                items = soup.find_all('div', class_='nft-item')
                
                for item in items[:10]:
                    price_elem = item.find('div', class_='nft-price')
                    if price_elem:
                        price_text = price_elem.text.strip()
                        price = cls._parse_price(price_text)
                        if price > 0:
                            prices.append(price)
                
                if prices:
                    avg_price = sum(prices) / len(prices)
                    number_mult = cls._get_number_multiplier(nft_number)
                    
                    # Итоговая рыночная цена (в TON)
                    market_price_ton = avg_price * number_mult
                    
                    # Конвертируем в рубли и звезды
                    ton_to_rub = await cls._get_ton_rate()
                    market_price_rub = market_price_ton * ton_to_rub
                    market_price_stars = market_price_rub / STARS_TO_RUB
                    
                    return {
                        'success': True,
                        'source': 'fragment.com',
                        'market_ton': round(market_price_ton, 2),
                        'market_rub': round(market_price_rub),
                        'market_stars': round(market_price_stars),
                        'number_multiplier': number_mult,
                        'confidence': 'high'
                    }
            
            return {'success': False}
            
        except Exception as e:
            logger.error(f"Fragment parsing error: {e}")
            return {'success': False}

    @classmethod
    def _calculate_price(cls, nft_name, nft_number):
        """
        Алгоритмический расчет цены
        """
        # Нормализуем название
        normalized = cls._normalize_name(nft_name)
        
        # Базовая цена в TON
        base_price_ton = 50
        
        # Ищем в известных коллекциях
        collection_info = None
        for key, collection in cls.KNOWN_COLLECTIONS.items():
            if key in normalized:
                base_price_ton = collection['base_price']
                collection_info = collection
                break
        
        # Множитель номера
        number_multiplier = cls._get_number_multiplier(nft_number)
        
        # Итоговая цена в TON
        market_price_ton = base_price_ton * number_multiplier
        
        # Конвертируем
        ton_to_rub = asyncio.run(cls._get_ton_rate())
        market_price_rub = market_price_ton * ton_to_rub
        market_price_stars = market_price_rub / STARS_TO_RUB
        
        result = {
            'success': True,
            'source': 'algorithm',
            'market_ton': round(market_price_ton, 2),
            'market_rub': round(market_price_rub),
            'market_stars': round(market_price_stars),
            'number_multiplier': number_multiplier,
            'confidence': 'medium'
        }
        
        if collection_info:
            result['collection'] = collection_info['name']
            result['rarity'] = collection_info['rarity']
        
        return result

    @classmethod
    def _get_number_multiplier(cls, number):
        """Множитель для номера NFT"""
        number_str = str(number).strip()
        
        if number_str in cls.NUMBER_MULTIPLIERS:
            return cls.NUMBER_MULTIPLIERS[number_str]
        
        try:
            num = int(number_str)
            
            if num < 10:
                return 2.0
            elif num < 100:
                if num % 10 == 0:
                    return 1.5
                elif num % 11 == 0:
                    return 1.8
            elif num < 1000:
                if num % 100 == 0:
                    return 2.0
                elif num % 111 == 0:
                    return 3.0
                elif str(num) == str(num)[::-1]:
                    return 1.8
            elif num < 10000:
                if num % 1000 == 0:
                    return 2.5
                elif num % 1111 == 0:
                    return 4.0
        except:
            pass
        
        return 1.0

    @classmethod
    def _normalize_name(cls, name):
        """Нормализует название для поиска"""
        return re.sub(r'[^a-zA-Z0-9]', '', name.lower())

    @classmethod
    def _parse_price(cls, price_text):
        """Парсит цену из текста"""
        try:
            numbers = re.findall(r'[\d.]+', price_text)
            if numbers:
                return float(numbers[0])
        except:
            pass
        return 0

    @classmethod
    async def _get_ton_rate(cls):
        """Получает курс TON к RUB"""
        try:
            response = requests.get(
                'https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=rub',
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return data['the-open-network']['rub']
        except:
            pass
        return 90


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
        
        # Форматируем название для отображения
        display_name = name.replace('-', ' ').title()
        
        return {
            'name': name,
            'number': number,
            'full_link': link,
            'display_name': f"{display_name} #{number}"
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
        f"🌟 Добро пожаловать в Автоматическую Скупку NFT-подарков, {user.first_name}!\n\n"
        "Мы используем реальные данные с Fragment.com для оценки ваших NFT\n\n"
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
    
    handlers = {
        'sell': start_selling,
        'how_it_works': show_instructions,
        'support': show_support,
        'payment_rub': select_payment_method,
        'payment_stars': select_payment_method,
        'confirm_sale': confirm_sale,
        'cancel_sale': cancel_sale,
        'back_to_main': back_to_main,
        'check_another': check_another
    }
    
    handler = handlers.get(query.data)
    if handler:
        await handler(query, context)

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
        "🔍 **Анализируем ваш NFT...**\nПолучаем данные с Fragment.com...",
        parse_mode='Markdown'
    )
    
    # Получаем цену с Fragment
    price_data = await FragmentParser.get_nft_price(nft_data['name'], nft_data['number'])
    
    # Удаляем сообщение об анализе
    await analyzing_msg.delete()
    
    # Рассчитываем наше предложение (+30%)
    our_price_rub = int(price_data['market_rub'] * 1.3)
    our_price_stars = int(price_data['market_stars'] * 1.3)
    
    # Сохраняем данные
    context.user_data['nft_info'] = {
        'link': nft_data['full_link'],
        'name': nft_data['display_name'],
        'market_rub': price_data['market_rub'],
        'market_stars': price_data['market_stars'],
        'our_rub': our_price_rub,
        'our_stars': our_price_stars,
        'source': price_data['source'],
        'confidence': price_data.get('confidence', 'medium')
    }
    
    # Формируем сообщение с результатом
    source_emoji = "🌐" if price_data['source'] == 'fragment.com' else "📊"
    
    text = (
        f"✅ **🔍 Анализ NFT завершён!**\n\n"
        f"📎 **NFT:** {nft_data['display_name']}\n"
        f"{source_emoji} **Источник:** {price_data['source']}\n"
        f"🏷 **Рыночная стоимость:** {price_data['market_rub']:,} ₽ / {price_data['market_stars']:,} ⭐️\n"
        f"💰 **Наше предложение (+30%):** {our_price_rub:,} ₽ / {our_price_stars:,} ⭐️\n\n"
        f"**Выберите способ получения оплаты:**"
    )
    
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
        amount = nft_info.get('our_rub', 0)
        currency = '₽'
        currency_name = 'рублях'
    else:
        amount = nft_info.get('our_stars', 0)
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
        amount = nft_info.get('our_rub', 0)
        currency = '₽'
        currency_name = 'рубли'
    else:
        amount = nft_info.get('our_stars', 0)
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
        "2️⃣ Бот анализирует цену с Fragment.com\n"
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
