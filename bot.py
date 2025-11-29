import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)
import requests
from datetime import datetime

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Переменные окружения
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# Состояния для диалога
CHOOSING_SERVICE, GETTING_NAME, GETTING_CONTACT = range(3)

# Системный промпт для DeepSeek
SYSTEM_PROMPT = """Ты — профессиональный консультант по Васту (древней индийской науке гармонии пространства).

ВАЖНЫЕ ПРАВИЛА:
1. Отвечай тёплым, дружелюбным, но деловым тоном
2. Не будь колдуньей или мистиком — будь профессионалом
3. Давай конкретные, практические советы
4. Упоминай принципы Васту, но объясняй их доступно
5. Длина ответа: 2-4 абзаца (не более 500 символов)
6. В конце предлагай консультацию, если нужна помощь

Примеры хорошего ответа:
- "По принципам Васту спальня должна быть на юго-западе дома. Кровать располагай головой на юг или запад. Это создаёт спокойствие и хороший сон. Если комната расположена иначе, используй цветовые коррекции..."
- "Рабочее место нужно размещать на северо-востоке или северо-западе. Стол рекомендуется повернуть так, чтобы ты смотрел на север или восток. Это привлечёт деньги и вдохновение..."

Избегай:
- ❌ Магии и суеверий
- ❌ Длинных теоретических объяснений
- ❌ Спама о предсказаниях судьбы
"""

# Тарифы
TARIFFS = {
    "express": {
        "name": "Экспресс Васту-консультация",
        "price": "2850 ₽",
        "description": "Васту карта + 5 ключевых советов в PDF"
    },
    "apartment": {
        "name": "Полный Васту-проект для квартиры/офиса",
        "price": "от 14700 ₽",
        "description": "Полная диагностика, рекомендации по материалам, цветам, коррекциям"
    },
    "land": {
        "name": "Васту-анализ участка",
        "price": "от 15600 ₽",
        "description": "Анализ участка земли, рекомендации по размещению дома"
    }
}

# Мини-кейсы
MINI_CASES = {
    "workspace": {
        "title": "💼 Рабочее место дома — как зарабатывать на удалёнке",
        "content": """🏠 **Васту советы для рабочего места:**

1️⃣ **Локация:** Северо-восток или северо-запад комнаты (зоны успеха и денег)

2️⃣ **Стол:** Расположи так, чтобы ты смотрел на север или восток

3️⃣ **Цвета:** 
   - Для энергии: жёлтый, оранжевый
   - Для спокойствия: светло-зелёный, голубой

4️⃣ **Кактусы и растения:** Избегай острых кактусов (отгоняют клиентов)

5️⃣ **Коррекции:** Если рабочее место на юго-западе — используй зелёный свет

Результат: ✨ Больше фокуса, привлечение клиентов, гармония в работе"""
    },
    "newyear": {
        "title": "🎄 Подготовка дома к Новому году по Васту",
        "content": """🏡 **Васту советы для новогодней энергии:**

1️⃣ **Уборка:** Избавься от старого, ненужного (это новое начало!)

2️⃣ **Входная дверь:** Её направление влияет на энергию
   - Север: успех в бизнесе
   - Восток: здоровье и рост
   - Юго-запад: стабильность семьи

3️⃣ **Цветовая схема на праздник:**
   - Красный + золотой = удача и процветание
   - Зелёный = здоровье и рост
   - Синий = спокойствие и гармония

4️⃣ **Ёлка:** Размещай на северо-востоке или в центре комнаты

5️⃣ **Очищение пространства:** Зажги свечу или используй благовония

Результат: ✨ Новый год принесёт свежую энергию и благополучие!"""
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user_name = update.effective_user.first_name
    
    welcome_text = f"""🌸 **Добро пожаловать, {user_name}!**

Я — помощник канала **VASTU FLOW | Гармоничный дом**

Я помогу тебе:
✨ Ответить на вопросы про Васту (с помощью AI)
📚 Показать примеры проектов
💬 Пригласить на консультацию

**Что тебя интересует?**"""
    
    keyboard = [
        [InlineKeyboardButton("❓ Задать вопрос про Васту", callback_data='ask_question')],
        [InlineKeyboardButton("📋 Услуги и тарифы", callback_data='show_tariffs')],
        [InlineKeyboardButton("📚 Мини-кейсы", callback_data='show_cases')],
        [InlineKeyboardButton("📞 Заказать консультацию", callback_data='order_consultation')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'ask_question':
        await query.edit_message_text(
            text="🤔 Напиши свой вопрос про Васту:\n\n(Например: 'Как расставить мебель в спальне?' или 'Какой цвет стен выбрать?')"
        )
        context.user_data['awaiting_question'] = True
    
    elif query.data == 'show_tariffs':
        tariff_text = "💳 **Наши услуги и тарифы:**\n\n"
        for key, tariff in TARIFFS.items():
            tariff_text += f"**{tariff['name']}**\n💰 {tariff['price']}\n📝 {tariff['description']}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("📞 Заказать", callback_data='order_consultation')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=tariff_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == 'show_cases':
        keyboard = [
            [InlineKeyboardButton("💼 Рабочее место дома", callback_data='case_workspace')],
            [InlineKeyboardButton("🎄 Подготовка к Новому году", callback_data='case_newyear')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="📚 **Выбери интересующий тебя кейс:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data.startswith('case_'):
        case_type = query.data.replace('case_', '')
        case = MINI_CASES[case_type]
        
        keyboard = [
            [InlineKeyboardButton("📞 Заказать консультацию", callback_data='order_consultation')],
            [InlineKeyboardButton("📚 Другие кейсы", callback_data='show_cases')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=f"{case['title']}\n{case['content']}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == 'order_consultation':
        await query.edit_message_text(text="📋 **Оформление консультации**\n\nКак тебя зовут?")
        context.user_data['ordering'] = True
        return GETTING_NAME
    
    elif query.data == 'main_menu':
        await start(update, context)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    
    if context.user_data.get('awaiting_question'):
        user_question = update.message.text
        context.user_data['awaiting_question'] = False
        
        wait_message = await update.message.reply_text("⏳ Ищу ответ в древней науке Васту...")
        
        try:
            response = requests.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_question}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                timeout=30
            )
            
            if response.status_code == 200:
                answer = response.json()['choices'][0]['message']['content']
                await wait_message.delete()
                
                answer_text = f"""✨ **Ответ про Васту:**

{answer}

---

💡 *Хочешь получить полную консультацию с проектом?*"""
                
                keyboard = [
                    [InlineKeyboardButton("📞 Заказать консультацию", callback_data='order_consultation')],
                    [InlineKeyboardButton("❓ Ещё вопрос", callback_data='ask_question')],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    answer_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await wait_message.edit_text("❌ Ошибка при получении ответа. Попробуй позже.")
        
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await wait_message.edit_text(f"❌ Ошибка: {str(e)[:100]}")
    
    elif context.user_data.get('ordering'):
        context.user_data['name'] = update.message.text
        context.user_data['ordering'] = False
        context.user_data['getting_contact'] = True
        await update.message.reply_text("Спасибо! 😊\n\nТвой номер телефона или Telegram для связи?")
    
    elif context.user_data.get('getting_contact'):
        contact = update.message.text
        name = context.user_data.get('name', 'Не указано')
        
        logger.info(f"📝 НОВЫЙ ЗАКАЗ:\nИмя: {name}\nКонтакт: {contact}\nДата: {datetime.now()}")
        
        context.user_data['getting_contact'] = False
        
        confirmation_text = f"""✅ **Спасибо за заказ!**

📋 **Твои данные:**
👤 Имя: {name}
📞 Контакт: {contact}

Я свяжусь с тобой в ближайшее время! 🌸

В это время можешь:"""
        
        keyboard = [
            [InlineKeyboardButton("❓ Ещё вопрос про Васту", callback_data='ask_question')],
            [InlineKeyboardButton("📚 Посмотреть кейсы", callback_data='show_cases')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            confirmation_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

def main():
    """Запуск бота"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("🤖 Бот VASTU FLOW запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
