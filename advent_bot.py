import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.error import TelegramError
import os
from pathlib import Path
from datetime import datetime, timedelta
import json
import asyncio

# Конфигурация
TOKEN = "BOT_TOKEN" # не забыть вставить
IMAGES_DIR = "data/images"
CLUES_FILE = "data/clues.txt"
TEXTS_FILE = "data/authors.txt"
QUESTIONS_FILE = "data/questions.txt"
AUTHORS_FILE = "data/authors.txt"
USERS_FILE = "data/users.json"

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы
START_DATE = datetime(2025, 12, 8)
TOTAL_DAYS = 21
END_DATE = START_DATE + timedelta(days=TOTAL_DAYS - 1)
SEND_TIME = "10:00"

# Текст приветствия
WELCOME_TEXT = """Добро пожаловать!

Перед вами — литературно-детективный адвент-календарь🕵️

Как он работает: 
1. Каждый день вы получаете иллюстрацию с вопросом. 

Это короткая рефлексия в форме «вопроса писателю». 

2. После просмотра нажмите 

«найти улику». 

Бот пришлёт деталь, шифр или подсказку — один шаг в ежедневной цепочке загадок. 

3. Все дни идут по порядку. Пропустили — сможете догнать. 

4. В конце вас ждёт итоговое задание, где пригодятся все найденные улики и, конечно, ваша интуиция. 

Держите глаза открытыми, отвечайте честно, собирайте детали — и наслаждайтесь атмосферой вместе с книжным клубом «Обещаю, завтра прочитаю!» (https://t.me/ricksschwifty)"""

BACKSTORY_TEXT = """В закрытом клубе писателей должен был состояться аукцион редчайшей книги. Говорили, что она меняет судьбу того, кто её откроет…

Впрочем, это лишь слухи. 

Вечер обещал быть роскошным: шампанское, споры, блеск и лёгкое предновогоднее волнение. 

Но в момент, когда ведущий снял вуаль с лота, гости замолкли: книга исчезла. 

Теперь каждый взгляд — подозрение, каждый жест — возможная улика. 

С этого момента вам предстоит расшифровывать намёки, задавать вопросы гостям и искать то, что спрятано между слов. 

У вас есть 21 день, чтобы вернуть книгу. 

И помните: в этом расследовании вы — не только наблюдатель. Вы один из тех, кто был в зале."""


def load_users():
    """Загрузить список пользователей"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_users(users):
    """Сохранить список пользователей"""
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def get_current_day():
    """Получить текущий день адвент-календаря (1-21)"""
    now = datetime.now()
    delta = (now.date() - START_DATE.date()).days + 1
    if delta < 1:
        return 0  # Календарь еще не начался
    if delta > TOTAL_DAYS:
        return TOTAL_DAYS  # Календарь закончился
    return delta


def load_clues():
    """Загрузить улики из файла"""
    with open(CLUES_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines() if line.strip()]


def load_texts():
    """Загрузить части текста из файла"""
    with open(TEXTS_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines() if line.strip()]


def load_questions():
    """Загрузить вопросы из файла"""
    with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines() if line.strip()]


def load_authors():
    """Загрузить авторов из файла"""
    with open(AUTHORS_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines() if line.strip()]


def get_clue(day: int) -> str:
    """Получить улику для дня (day: 1-21)"""
    clues = load_clues()
    if 1 <= day <= len(clues):
        return clues[day - 1]
    return "Улика не найдена"


def get_text_part(day: int) -> str:
    """Получить часть текста для дня (если день кратен 3)"""
    if day % 3 != 0:
        return None
    texts = load_texts()
    part_num = day // 3
    if 1 <= part_num <= len(texts):
        return texts[part_num - 1]
    return None


def get_question(day: int) -> str:
    """Получить вопрос для дня"""
    questions = load_questions()
    if 1 <= day <= len(questions):
        return questions[day - 1]
    return "Вопрос дня"


def get_author(day: int) -> str:
    """Получить автора для дня"""
    authors = load_authors()
    if 1 <= day <= len(authors):
        return authors[day - 1]
    return "Автор"


def get_image_path(day: int) -> str:
    """Получить путь к картинке для дня"""
    image_path = os.path.join(IMAGES_DIR, f"{day}.jpg")
    if not os.path.exists(image_path):
        image_path = os.path.join(IMAGES_DIR, f"{day}.png")
    return image_path if os.path.exists(image_path) else None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user_id = str(update.effective_user.id)
    users = load_users()

    if user_id not in users:
        users[user_id] = {
            "joined_date": datetime.now().isoformat(),
            "current_day": 0,
            "subscribed": False  # Еще не подписан
        }
        save_users(users)

    # Первое приветственное сообщение с информацией
    keyboard = [[InlineKeyboardButton("Узнать предысторию", callback_data="backstory")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(WELCOME_TEXT, reply_markup=reply_markup, parse_mode="HTML")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия кнопок"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    users = load_users()

    data = query.data

    if data == "backstory":
        # Показать предысторию с кнопкой присоединения
        keyboard = [[InlineKeyboardButton("Присоединяюсь", callback_data="subscribe")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.answer()
        await query.edit_message_text(
            text=BACKSTORY_TEXT,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

    elif data == "subscribe":
        # Подписать пользователя на рассылку
        if user_id in users:
            users[user_id]["subscribed"] = True
            save_users(users)

        await query.answer("✅ Вы подписаны! Начинайте расследование!", show_alert=True)

        # Отправить историю, если она доступна
        current_day = get_current_day()
        if current_day > 1:
            await query.edit_message_text(
                text="📖 Загружаю для вас всю историю до текущего момента...",
                reply_markup=None
            )
            await asyncio.sleep(0.5)

            for day in range(1, current_day):
                await send_daily_message(query.message.chat_id, day, context)
                await asyncio.sleep(0.5)

            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="✅ История загружена! Теперь ты в курсе всех событий."
            )

    elif data.startswith("clue_"):
        # Обработка улики
        day = int(data.split("_")[1])
        clue = get_clue(day)
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"🔍 <b>Улика дня {day}:</b>\n\n{clue}", parse_mode="HTML")

    elif data.startswith("text_"):
        # Обработка части текста
        day = int(data.split("_")[1])
        text_part = get_text_part(day)
        if text_part:
            part_num = day // 3
            await query.answer()
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(
                f"📖 <b>Часть текста {part_num}:</b>\n\n{text_part}",
                parse_mode="HTML"
            )
        else:
            await query.answer("❌ Часть текста не найдена", show_alert=True)


async def send_daily_message(chat_id: int, day: int, context: ContextTypes.DEFAULT_TYPE):
    """Отправить ежедневное сообщение для конкретного дня"""
    if day < 1 or day > TOTAL_DAYS:
        return

    image_path = get_image_path(day)
    question = get_question(day)
    author = get_author(day)

    # Подпись к картинке: "ДЕНЬ n - <автор>"
    caption = f"<b>ДЕНЬ {day} - {author}</b>\n\n❓ {question}"

    # Создаем кнопку улики
    clue_button = InlineKeyboardButton(
        "🔍 Найти улику",
        callback_data=f"clue_{day}"
    )

    buttons = [[clue_button]]

    # Добавляем кнопку текста, если день кратен 3
    if day % 3 == 0:
        text_button = InlineKeyboardButton(
            "📖 Часть текста",
            callback_data=f"text_{day}"
        )
        buttons.append([text_button])

    keyboard = InlineKeyboardMarkup(buttons)

    try:
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    except TelegramError as e:
        logger.error(f"Ошибка отправки сообщения для дня {day}: {e}")


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /история - отправить все прошлые материалы"""
    current_day = get_current_day()

    if current_day == 0:
        await update.message.reply_text("⏳ Календарь еще не начался!")
        return

    if current_day > TOTAL_DAYS:
        start_day = 1
        end_day = TOTAL_DAYS
        await update.message.reply_text(f"📖 Отправляю все {TOTAL_DAYS} дней...")
    else:
        start_day = 1
        end_day = current_day - 1
        if end_day < start_day:
            await update.message.reply_text("📍 Сегодня первый день! Нечего отправлять.")
            return
        await update.message.reply_text(f"📖 Отправляю материалы с 1 по {end_day} день...")

    for day in range(start_day, end_day + 1):
        await send_daily_message(update.effective_chat.id, day, context)
        await asyncio.sleep(0.5)

    await update.message.reply_text("✅ История загружена!")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = (
        "🎄 <b>Команды адвент-календаря:</b>\n\n"
        "/start - Начать работу с ботом\n"
        "/история - Получить все прошлые материалы\n"
        "/help - Справка\n\n"
        "Каждый день в 10:00 МСК ты получишь новый материал!"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")


async def daily_task(context: ContextTypes.DEFAULT_TYPE):
    """Ежедневная задача - отправить сообщения всем подписанным пользователям"""
    current_day = get_current_day()

    if current_day < 1 or current_day > TOTAL_DAYS:
        return

    users = load_users()
    failed_users = []

    for user_id, user_data in users.items():
        # Отправляем только подписанным пользователям
        if not user_data.get("subscribed", False):
            continue

        try:
            await send_daily_message(int(user_id), current_day, context)
            logger.info(f"Отправлено сообщение пользователю {user_id} на день {current_day}")
        except TelegramError as e:
            logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
            failed_users.append(user_id)
        except Exception as e:
            logger.error(f"Неожиданная ошибка для пользователя {user_id}: {e}")

    if failed_users:
        logger.warning(f"Не удалось отправить {len(failed_users)} пользователям")


def main():
    """Основная функция"""
    # Проверка файлов
    required_files = [CLUES_FILE, TEXTS_FILE, QUESTIONS_FILE, AUTHORS_FILE]
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ Ошибка: файл {file} не найден!")
            return

    if not os.path.exists(IMAGES_DIR):
        print(f"❌ Ошибка: папка {IMAGES_DIR} не найдена!")
        return

    # Создание приложения
    application = Application.builder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("история", history))
    application.add_handler(CommandHandler("help", help_command))

    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))

    # Ежедневная задача в 10:00 МСК
    job_queue = application.job_queue
    job_queue.run_daily(
        daily_task,
        time=datetime.strptime("10:00", "%H:%M").time(),
        name="daily_advent"
    )

    logger.info("✅ Бот запущен!")
    application.run_polling()


if __name__ == '__main__':
    main()
