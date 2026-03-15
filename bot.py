import logging
import re
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
import json
import os
from datetime import datetime
import httpx
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = "8527173088:AAFENDpLWuQmRJe9ioRN4a1IbcnyqGgOkag"
ADMIN_IDS = []  # Добавьте свой ID после проверки

# Курсы конвертации (можно обновлять через админку)
STARS_TO_RUB = 1.6  # 1 звезда = 1.6 рубля (примерный курс)
RUB_TO_STARS = 0.625  # 1 рубль = 0.625 звезд

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

# Класс для оценки NFT по ссылке
class NFTParser:
    # Регулярное выражение для ссылок на NFT подарки
    NFT_PATTERN = r'https?://t\.me/nft/([a-zA-Z0-9_-]+)-(\d+)'
    
    # База данных редких NFT (можно расширять)
    RARE_NFT_DB = {
        # Формат: "название-номер": множитель
        "star-1": 10.0,  # Самый первый NFT
        "heart-1": 8.0,
        "diamond-1": 15.0,
        "alien-42": 5.0,  # Особенные номера
        "gold-100": 3.0,
        "mythic-777": 7.0,
    }
    
    # Множители для названий
    NAME_MULTIPLIERS = {
        # Обычные
        'star': 1.0,
        'heart': 1.2,
        'diamond': 2.5,
        'crown': 1.8,
        'rocket': 2.0,
        'alien': 3.0,
        
        # Редкие
        'gold': 2.2,
        'silver': 1.5,
        'bronze': 1.3,
        'mythic': 4.0,
        'legendary': 3.5,
        'epic': 2.8,
        'rare': 1.8,
        'ancient': 3.2,
        'space': 2.4,
        'rainbow': 2.1,
        'neon': 1.9,
        'glitch': 2.6,
    }
    
    # Множители для "красивых" номеров
    @classmethod
    def get_number_multiplier(cls, number_str):
        """Определяет множитель на основе номера NFT"""
        try:
            number = int(number_str)
            
            # Паттерны для "красивых" номеров
            if number < 10:  # Однозначные номера
                return 2.0
            elif number < 100:  # Двузначные
                if number % 10 == 0:  # Круглые числа (10, 20, 30...)
                    return 1.5
                elif number == number[::-1]:  # Палиндромы (11, 22, 33...)
                    return 1.8
            elif number < 1000:  # Трехзначные
                if number % 100 == 0:  # Круглые (100, 200...)
                    return 1.8
                elif number % 111 == 0:  # Одинаковые цифры (111, 222...)
                    return 2.2
                elif str(number) == str(number)[::-1]:  # Палиндромы (121, 131...)
                    return 1.6
            elif number < 10000:  # Четырехзначные
                if number % 1000 == 0:  # Круглые (1000, 2000...)
                    return 2.0
                elif number % 1111 == 0:  # Одинаковые (1111, 2222...)
                    return 3.0
            
            # Номера с повторяющимися цифрами
            num_str = str(number)
            if len(set(num_str)) == 1:  # Все цифры одинаковые
                return 2.5
            elif len(set(num_str)) == 2:  # Две разные цифры
                return 1.3
            
            return 1.0
        except:
            return 1.0
    
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
    
    @classmethod
    def calculate_price(cls, nft_name, nft_number):
        """Рассчитывает стоимость NFT в рублях и звездах"""
        # Базовая стоимость в рублях
        base_price_rub = 500
        
        # Проверяем, есть ли в базе редких NFT
        rare_key = f"{nft_name}-{nft_number}"
        if rare_key in cls.RARE_NFT_DB:
            multiplier = cls.RARE_NFT_DB[rare_key]
        else:
            # Множитель от названия
            name_lower = nft_name.lower()
            name_multiplier = 1.0
            
            # Ищем совпадение в названии
            for key, value in cls.NAME_MULTIPLIERS.items():
                if key in name_lower:
                    name_multiplier = value
                    break
            
            # Множитель от номера
            number_multiplier = cls.get_number_multiplier(nft_number)
            
            # Общий множитель
            multiplier = name_multiplier * number_multiplier
        
        # Добавляем случайный фактор для разнообразия
        random_factor = random.uniform(0.95, 1.05)
        
        # Рыночная стоимость
        market_price_rub = round(base_price_rub * multiplier * random_factor)
        
        # Наше предложение (+30%)
        our_price_rub = round(market_price_rub * 1.3)
        
        # Конвертация в звезды
        market_price_stars = round(market_price_rub / STARS_TO_RUB)
        our_price_stars = round(our_price_rub / STARS_TO_RUB)
        
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
    elif query.data.startswith('payment_'):
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
    """Начало процесса продажи - запрос ссылки"""
    context.user_data['state'] = 'waiting_for_link'
    
    text = (
        "🔗 **Отправьте ссылку на ваш NFT-подарок**\n\n"
        "Формат: `https://t.me/nft/НАЗВАНИЕ-НОМЕР`\n\n"
        "📌 **Примеры:**\n"
        "• `https://t.me/nft/star-123456`\n"
        "• `https://t.me/nft/heart-789012`\n"
        "• `https://t.me/nft/diamond-42`\n\n"
        "⚠️ Принимаются только NFT-подарки Telegram. "
        "Убедитесь что ссылка ведёт именно на NFT, а не на что-то другое."
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text, 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_nft_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка полученной ссылки на NFT"""
    if context.user_data.get('state') != 'waiting_for_link':
        return
    
    link = update.message.text.strip()
    
    # Парсим ссылку
    nft_data = NFTParser.parse_nft_link(link)
    
    if not nft_data:
        # Неправильный формат ссылки
        text = (
            "❌ **Неправильный формат ссылки!**\n\n"
            "Пожалуйста, отправьте ссылку в формате:\n"
            "`https://t.me/nft/НАЗВАНИЕ-НОМЕР`\n\n"
            "📌 **Примеры правильных ссылок:**\n"
            "• `https://t.me/nft/star-123456`\n"
            "• `https://t.me/nft/heart-789012`\n\n"
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
    
    # Имитируем процесс анализа (можно убрать задержку)
    await asyncio.sleep(2)
    
    # Рассчитываем стоимость
    price_info = NFTParser.calculate_price(nft_data['name'], nft_data['number'])
    
    # Сохраняем данные
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
    
    # Удаляем сообщение об анализе
    await analyzing_msg.delete()
    
    # Показываем результат оценки
    text = (
        "✅ **🔍 Анализ NFT завершён!**\n\n"
        f"📎 **NFT:** {nft_data['full_link']}\n"
        f"🏷 **Рыночная стоимость:** ~{price_info['market_rub']} ₽ / {price_info['market_stars']} ⭐️\n"
        f"💰 **Наше предложение:** {price_info['our_rub']} ₽ / {price_info['our_stars']} ⭐️\n\n"
        f"✨ **Редкость:** x{price_info['multiplier']}\n\n"
        "**Выберите способ получения оплаты:**"
    )
    
    keyboard = [
        [InlineKeyboardButton("💵 Рубли (₽)", callback_data='payment_rub')],
        [InlineKeyboardButton("⭐️ Звезды (Telegram Stars)", callback_data='payment_stars')],
        [InlineKeyboardButton("🔄 Проверить другой NFT", callback_data='check_another')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel_sale')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # Меняем состояние
    context.user_data['state'] = 'awaiting_payment'

async def select_payment_method(query, context):
    """Выбор способа оплаты"""
    payment_method = query.data.replace('payment_', '')
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
        f"💰 **Сумма к выплате:** {amount} {currency}\n\n"
        "Пожалуйста, подтвердите продажу:"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить продажу", callback_data='confirm_sale')],
        [InlineKeyboardButton("◀️ Назад к выбору оплаты", callback_data='back_to_payment')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel_sale')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def confirm_sale(query, context):
    """Подтверждение продажи"""
    user_id = query.from_user.id
    nft_info = context.user_data.get('nft_info', {})
    payment_method = context.user_data.get('payment_method', 'rub')
    
    if not nft_info:
        await query.edit_message_text("❌ Ошибка: данные не найдены. Начните заново.")
        return
    
    # Определяем сумму в зависимости от способа оплаты
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
        "user_id": user_id,
        "username": query.from_user.username,
        "nft_info": nft_info,
        "payment_method": payment_method,
        "amount": amount,
        "currency": currency,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    data["transactions"].append(transaction)
    save_data(data)
    
    # Уведомление админам
    for admin_id in ADMIN_IDS:
        try:
            admin_text = (
                f"🆕 **Новая заявка на продажу!**\n\n"
                f"👤 **Пользователь:** @{query.from_user.username}\n"
                f"🆔 **ID:** {user_id}\n"
                f"🔗 **NFT:** {nft_info.get('link')}\n"
                f"📛 **Название:** {nft_info.get('name')}\n"
                f"🔢 **Номер:** {nft_info.get('number')}\n"
                f"💳 **Способ оплаты:** {currency_name}\n"
                f"💰 **Сумма:** {amount} {currency}\n"
                f"📊 **Редкость:** x{nft_info.get('multiplier')}\n"
                f"📋 **ID транзакции:** {transaction['id']}"
            )
            
            await context.bot.send_message(
                admin_id, 
                admin_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    success_text = (
        "✅ **Заявка на продажу принята!**\n\n"
        f"💰 **Сумма:** {amount} {currency}\n"
        f"💳 **Способ оплаты:** {currency_name}\n\n"
        "С вами свяжется наш менеджер в ближайшее время для завершения сделки.\n"
        "Пожалуйста, ожидайте сообщения.\n\n"
        "Спасибо за доверие! 🙏"
    )
    
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        success_text, 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    context.user_data.clear()

async def check_another(query, context):
    """Проверка другого NFT"""
    context.user_data['state'] = 'waiting_for_link'
    
    text = (
        "🔗 **Отправьте ссылку на другой NFT-подарок**\n\n"
        "Формат: `https://t.me/nft/НАЗВАНИЕ-НОМЕР`"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text, 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

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
        "📋 **Как проходит сделка:**\n\n"
        "1️⃣ Вы отправляете ссылку на ваш NFT-подарок\n"
        "2️⃣ Бот автоматически анализирует его редкость и стоимость\n"
        "3️⃣ Вы получаете предложение на 30% выше рыночной цены\n"
        "4️⃣ Вы выбираете способ оплаты (рубли или звезды)\n"
        "5️⃣ Наш менеджер связывается с вами в Telegram\n"
        "6️⃣ Вы передаете NFT\n"
        "7️⃣ Мгновенная выплата выбранным способом\n\n"
        "⚡ Вся сделка занимает не более 10 минут!"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        instructions, 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_support(query, context):
    """Поддержка"""
    support_text = (
        "🆘 **Поддержка**\n\n"
        "Если у вас возникли вопросы или проблемы:\n\n"
        "📱 **Напишите менеджеру:** @support_username\n"
        "📧 **Email:** support@example.com\n"
        "⏰ **Время работы:** 24/7\n\n"
        "Среднее время ответа: 5-10 минут"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        support_text, 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def back_to_main(query, context):
    """Возврат в главное меню"""
    context.user_data.clear()
    
    text = "🏠 **Главное меню**\n\nВыберите действие:"
    
    keyboard = [
        [InlineKeyboardButton("💰 Продать NFT", callback_data='sell')],
        [InlineKeyboardButton("📋 Как проводится сделка?", callback_data='how_it_works')],
        [InlineKeyboardButton("🆘 Поддержка", callback_data='support')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text, 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика для админов"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return
    
    data = load_data()
    total_users = len(data["users"])
    total_transactions = len(data["transactions"])
    pending = sum(1 for t in data["transactions"] if t["status"] == "pending")
    completed = sum(1 for t in data["transactions"] if t["status"] == "completed")
    total_volume_rub = sum(t["amount"] for t in data["transactions"] 
                          if t["status"] == "completed" and t.get("currency") == "₽")
    total_volume_stars = sum(t["amount"] for t in data["transactions"] 
                            if t["status"] == "completed" and t.get("currency") == "⭐️")
    
    stats = (
        f"📊 **Статистика бота**\n\n"
        f"👥 **Пользователей:** {total_users}\n"
        f"📦 **Всего транзакций:** {total_transactions}\n"
        f"⏳ **В обработке:** {pending}\n"
        f"✅ **Завершено:** {completed}\n"
        f"💰 **Выплачено рублей:** {total_volume_rub:,.0f} ₽\n"
        f"⭐️ **Выплачено звезд:** {total_volume_stars:,.0f} ⭐️\n"
    )
    
    await update.message.reply_text(stats, parse_mode='Markdown')

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
        
        # Обработчик текстовых сообщений (для ссылок)
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            handle_nft_link
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