
import telebot
import mysql.connector
from telebot import types
import re
import os

# ============================================
# 1. НАСТРОЙКИ (тебе нужно заполнить своими данными)
# ============================================

# Токен твоего бота. Получаешь у @BotFather в Telegram
TOKEN = os.environ.get('BOT_TOKEN')

DB_CONFIG = {
    'host': os.environ.get('DB_HOST'),
    'user': os.environ.get('DB_USER'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME'),
    'charset': 'utf8mb4'
}

# ID твоего Telegram аккаунта (ты как администратор)
# Узнать можно у бота @userinfobot
ADMIN_ID = 1200147731  # ВСТАВЬ СВОЙ ID

# Список каналов, на которые нужно подписаться (username каналов)
# Пример: '@kinopoisk' или 'https://t.me/kinopoisk'
REQUIRED_CHANNELS = ['@film_and_serialss']  # ВСТАВЬ СВОИ КАНАЛЫ

# ============================================
# 2. ИНИЦИАЛИЗАЦИЯ БОТА
# ============================================

bot = telebot.TeleBot(TOKEN)

# Функция для подключения к базе данных
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Ошибка подключения к БД: {err}")
        return None

# ============================================
# 3. ФУНКЦИЯ ПРОВЕРКИ ПОДПИСКИ
# ============================================

def check_subscription(user_id):
    """
    Проверяет, подписан ли пользователь на все обязательные каналы
    Возвращает True, если подписан на все, иначе False
    """
    not_subscribed = []
    
    for channel in REQUIRED_CHANNELS:
        try:
            # Пробуем получить информацию о пользователе в канале
            status = bot.get_chat_member(channel, user_id).status
            if status not in ['member', 'administrator', 'creator']:
                not_subscribed.append(channel)
        except Exception as e:
            # Если канал не найден или бот не админ в нем
            print(f"Ошибка проверки канала {channel}: {e}")
            not_subscribed.append(channel)
    
    return not_subscribed

# ============================================
# 4. ОБРАБОТЧИК КОМАНДЫ /start
# ============================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Отправляет приветственное сообщение с фото и показывает меню"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Создаем клавиатуру с кнопками
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("🎬 Получить фильм")
    btn2 = types.KeyboardButton("📋 Как это работает")
    markup.add(btn1, btn2)
    
    # Проверяем подписку при старте
    not_subscribed = check_subscription(user_id)
    
    if not_subscribed:
        # Создаем клавиатуру с кнопками-ссылками
        inline_markup = types.InlineKeyboardMarkup(row_width=1)
        
        for channel in not_subscribed:
            channel_button = types.InlineKeyboardButton(
                text="👁️ Канал",
                url=f"https://t.me/{channel.replace('@', '')}"
            )
            inline_markup.add(channel_button)
        
        check_button = types.InlineKeyboardButton(
            text="✅ Я подписался",
            callback_data="check_subscription"
        )
        inline_markup.add(check_button)
        
        # Отправляем фото с подписью и кнопками
        try:
            # Пробуем отправить локальный файл
            with open('privetbot.jpg', 'rb') as photo:
                bot.send_photo(
                    message.chat.id,
                    photo,
                    caption=f"Привет, {user_name}!\n\n"
                            "Чтобы пользоваться ботом, подпишись на эти каналы:",
                    reply_markup=inline_markup
                )
        except FileNotFoundError:
            # Если файл не найден, отправляем обычное сообщение
            bot.send_message(
                message.chat.id,
                f"Привет, {user_name}!\n\n"
                "Чтобы пользоваться ботом, подпишись на эти каналы:",
                reply_markup=inline_markup
            )
    else:
        # Если подписан - сразу даем доступ
        bot.send_message(
            message.chat.id,
            f"Привет, {user_name}! Ты уже подписан на все каналы. Нажимай '🎬 Получить фильм' и вводи код!",
            reply_markup=markup
        )

# ============================================
# 5. ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ (кнопки и коды)
# ============================================

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Обрабатывает нажатия кнопок и ввод кодов"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Обработка кнопки "Как это работает"
    if text == "📋 Как это работает":
        help_text = """
📽️ **Как получить фильм?**

1. Смотри мои видео в TikTok/YouTube
2. В описании найди код фильма (например: ф123)
3. Введи этот код сюда
4. Получи название и ссылку на просмотр

🔍 **Где брать коды?**
Коды я публикую только в видео.
        """
        bot.send_message(message.chat.id, help_text, parse_mode='Markdown')
        return
    
    # Обработка кнопки "Получить фильм"
    if text == "🎬 Получить фильм":
        # Проверяем подписку
        not_subscribed = check_subscription(user_id)
        
        if not_subscribed:
            channels_text = "Сначала подпишись на:\n"
            for ch in not_subscribed:
                channels_text += f"➡️ {ch}\n"
            bot.send_message(message.chat.id, channels_text)
        else:
            bot.send_message(
                message.chat.id, 
                "✅ Подписка проверена!\nВведи код фильма из видео:"
            )
        return
    
    # Если это не кнопка - значит пользователь ввел код
    # Проверяем подписку перед обработкой кода
    not_subscribed = check_subscription(user_id)
    
    if not_subscribed:
        channels_text = "Чтобы получить фильм, подпишись на:\n"
        for ch in not_subscribed:
            channels_text += f"➡️ {ch}\n"
        bot.send_message(message.chat.id, channels_text)
        return
    
    # ===== Ищем фильм по коду в базе данных =====
    
    # Очищаем код от лишних пробелов и приводим к нижнему регистру
    # (чтобы "Ф123" и "ф123" считались одинаковыми)
    kod = text.strip().lower()
    
    # Подключаемся к БД
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "😔 Техническая ошибка. Попробуй позже.")
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Ищем фильм по коду
        # Знак % позволяет искать частичное совпадение (если код может быть частью строки)
        query = "SELECT name, link FROM films WHERE kod = %s OR kod LIKE %s"
        cursor.execute(query, (kod, f"%{kod}%"))
        result = cursor.fetchone()
        
        if result:
            # Фильм найден
            film_name = result['name']
            film_link = result.get('link', '')
            
            response = f"🎬 **Нашел!**\n\n**Название:** {film_name}\n"
            if film_link:
                response += f"🔗 [Смотреть фильм]({film_link})"
            else:
                response += "🔗 Ссылка пока не добавлена"
            
            bot.send_message(message.chat.id, response, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            # Фильм не найден
            bot.send_message(
                message.chat.id, 
                "😕 Фильм с таким кодом не найден.\nПроверь код в видео или попробуй другой."
            )
    
    except mysql.connector.Error as err:
        print(f"Ошибка SQL: {err}")
        bot.send_message(message.chat.id, "😔 Ошибка базы данных. Мы уже чиним!")
    
    finally:
        cursor.close()
        conn.close()

# ============================================
# ОБРАБОТЧИК НАЖАТИЙ НА INLINE-КНОПКИ
# ============================================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Обрабатывает нажатия на inline-кнопки"""
    user_id = call.from_user.id
    
    if call.data == "check_subscription":
        # Проверяем подписку
        not_subscribed = check_subscription(user_id)
        
        if not_subscribed:
            # Если ещё не подписался
            bot.answer_callback_query(
                call.id,
                "Ты ещё не подписался на все каналы! 👆",
                show_alert=False
            )
        else:
            # Если подписался - убираем inline-кнопки и показываем меню
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn1 = types.KeyboardButton("🎬 Получить фильм")
            btn2 = types.KeyboardButton("📋 Как это работает")
            markup.add(btn1, btn2)
            
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption="✅ Подписка проверена! Теперь ты можешь пользоваться ботом."
            )
            bot.send_message(
                call.message.chat.id,
                "Нажимай '🎬 Получить фильм' и вводи код!",
                reply_markup=markup
            )

# ============================================
# 6. КОМАНДЫ ДЛЯ АДМИНИСТРАТОРА (добавление фильмов)
# ============================================

@bot.message_handler(commands=['addfilm'])
def add_film(message):
    """Добавляет новый фильм в базу (только для админа)"""
    
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ У тебя нет прав администратора.")
        return
    
    # Разбираем команду: /addfilm код123 Название фильма
    # Пример: /addfilm б123 Брат
    
    parts = message.text.split(maxsplit=2)
    
    if len(parts) < 3:
        bot.send_message(
            message.chat.id, 
            "❌ Неправильный формат.\nИспользуй: /addfilm код Название\nПример: /addfilm б123 Брат"
        )
        return
    
    kod = parts[1].strip().lower()
    name = parts[2].strip()
    
    # Подключаемся к БД
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "😔 Ошибка подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        
        # Вставляем новую запись
        query = "INSERT INTO films (kod, name) VALUES (%s, %s)"
        cursor.execute(query, (kod, name))
        conn.commit()
        
        bot.send_message(
            message.chat.id, 
            f"✅ Фильм добавлен!\nКод: {kod}\nНазвание: {name}"
        )
    
    except mysql.connector.Error as err:
        print(f"Ошибка SQL: {err}")
        bot.send_message(message.chat.id, f"❌ Ошибка: {err}")
    
    finally:
        cursor.close()
        conn.close()

@bot.message_handler(commands=['delfilm'])
def delete_film(message):
    """Удаляет фильм по коду (только для админа)"""
    
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ У тебя нет прав администратора.")
        return
    
    parts = message.text.split()
    
    if len(parts) < 2:
        bot.send_message(message.chat.id, "❌ Укажи код для удаления.\nПример: /delfilm б123")
        return
    
    kod = parts[1].strip().lower()
    
    conn = get_db_connection()
    if not conn:
        bot.send_message(message.chat.id, "😔 Ошибка подключения к БД")
        return
    
    try:
        cursor = conn.cursor()
        
        query = "DELETE FROM films WHERE kod = %s"
        cursor.execute(query, (kod,))
        conn.commit()
        
        if cursor.rowcount > 0:
            bot.send_message(message.chat.id, f"✅ Фильм с кодом {kod} удален.")
        else:
            bot.send_message(message.chat.id, f"❌ Фильм с кодом {kod} не найден.")
    
    except mysql.connector.Error as err:
        print(f"Ошибка SQL: {err}")
        bot.send_message(message.chat.id, f"❌ Ошибка: {err}")
    
    finally:
        cursor.close()
        conn.close()

# ============================================
# 7. ЗАПУСК БОТА
# ============================================

if __name__ == '__main__':
    print("Бот запущен...")
    # Проверяем подключение к БД при старте
    conn = get_db_connection()
    if conn:
        print("✅ Подключение к MySQL успешно")
        conn.close()
    else:
        print("❌ Ошибка подключения к MySQL")
    
    # Запускаем бота
    bot.infinity_polling()