import sys
import os
import logging
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from telegram import Update, Message
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from telegram.error import TelegramError


load_dotenv()


def init_config():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=[
            logging.FileHandler('log.txt', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logging.error('Не указан токен бота')
        sys.exit(1)

    admin_chat_ids = os.getenv("ADMIN_CHAT_ID")
    if admin_chat_ids:
        admin_chat_ids = [int(admin_id.strip()) for admin_id in admin_chat_ids.split(',') if admin_id.strip()]
    else:
        logging.error('Не заполнены администраторы')
        admin_chat_ids = []

    chat_ids = os.getenv('CHAT_ID')
    if chat_ids:
        chat_ids = [int(chat_id.strip()) for chat_id in chat_ids.split(',') if chat_id.strip()]
    else:
        logging.error('Не заполнен список чатов')
        chat_ids = []

    file_log_massage = os.getenv('FILE_LOG_MASSAGE')
    file_log_massage = Path(file_log_massage) if file_log_massage else None

    return token, admin_chat_ids, chat_ids, file_log_massage


TOKEN, ADMIN_CHAT_IDS, CHAT_IDS, FILE_LOG_MASSAGE = init_config()


async def write_log_message(message: Message):
    if not FILE_LOG_MASSAGE:
        logging.error('Не указан файл логирования сообщений')
        return
    elif not FILE_LOG_MASSAGE.exists():
        try:
            FILE_LOG_MASSAGE.touch()
        except Exception as exc:
            logging.error(f'Не удалось создать файл логирования, по причине: {exc}')
            return

    time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user = message.from_user
    text = message.text

    try:
        with open(FILE_LOG_MASSAGE, 'a', encoding='utf-8') as file:
            file.write(f'{time} - {user.full_name} ({user.id}) - {message.chat.id} - {text}\n')
    except Exception as exc:
        logging.error(f'Ошибка при записи сообщения в лог {exc}')


async def send_message_admins(message: Message, context):
    user = message.from_user
    text = message.text
    chat = message.chat

    try:
        chat_link = await context.bot.export_chat_invite_link(chat.id)
    except TelegramError:
        chat_link = 'Private chat (no link)'

    new_message_admin = (
        f'User: {user.mention_html()} \n'
        f'Chat: {chat_link} ({chat.id}) \n'
        f'Send message:\n{text}'
    )

    for admin_chat_id in ADMIN_CHAT_IDS:
        await send_message_admin(admin_chat_id, new_message_admin, context)


async def send_message_admin(admin_chat_id: int, text: str, context):
    try:
        await context.bot.send_message(
            chat_id=admin_chat_id,
            text=text,
            parse_mode="HTML"
        )
        logging.info(f"Сообщение отправлено админу: {text}")
    except Exception as exc:
        logging.error(f"Ошибка при отправке сообщения админу: {exc}")


def check_message(message: Message):
    return 'test' in message.text.lower()


def text_in_message(message: Message):
    return bool(message.text)


def write_info_message(message: Message):
    # TODO: Реализовать хранение последних 10 сообщений от каждого пользователя
    #       Это позволит исключить дубли и анализировать историю сообщений
    pass


async def log_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if message and message.chat.id in CHAT_IDS:

        if text_in_message(message):
            write_info_message(message)

            if check_message(message):
                await write_log_message(message)
                await send_message_admins(message, context)


app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, log_message))

if __name__ == "__main__":
    try:
        print("Бот запущен и слушает сообщения...")
        app.run_polling()
    except KeyboardInterrupt:
        print('Бот остановлен пользователем')
        sys.exit(0)
    except Exception as e:
        logging.error(f'Критическая ошибка: {e}')
        sys.exit(1)
