import os
import logging
import paramiko
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
from functools import partial
import json
from psycopg2 import sql
import psycopg2
from psycopg2 import Error
from pathlib import Path
import subprocess

logging.basicConfig(filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logging.info("Логгирование начато. Текущий уровень логгирования: " + logging._levelToName[logging.root.level])

TOKEN = os.getenv('TOKEN')
SSH_USERNAME = os.getenv('RM_USER')
SSH_PASSWORD = os.getenv('RM_PASSWORD')
SSH_HOST = os.getenv('RM_HOST')
SSH_PORT = os.getenv('RM_PORT')
PSQL_USERNAME = os.getenv('DB_USER')
PSQL_PASSWORD = os.getenv('DB_PASSWORD')
PSQL_HOST = os.getenv('DB_HOST')
PSQL_PORT = os.getenv('DB_PORT')
PSQL_DATABASE_NAME = os.getenv('DB_DATABASE')
logging.info("Скопированны переменные окружения")

logging.info("Считывание help сообщения")
help_message = "Хм, похоже, что help сообщеение где-то потерялось 🤔🤔🤔" # заполнение на случай, если не удасться считать из файла 
try:
    with open("help_message.txt", "r") as fp:
        help_message = fp.read()
except Exception as e:
    logging.critical("Ошибка при считывании help сообщения: " + repr(e))
logging.info("Считывание help сообщения закончено")

last_regexp_read = []

def ssh_connect():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=SSH_HOST, username=SSH_USERNAME, password=SSH_PASSWORD, port=SSH_PORT)
    except Exception as e:
        logging.error("Ошибка подключения к ssh: " + repr(e))
        return None
    logging.info("Произошло подключение к ssh")
    return client

def find_command(update: Update, context, reply_text: str, next_step: str):
    logging.info("Вызван find_command. Текст ответа: " + reply_text + "Следующий шаг: " + next_step)
    update.message.reply_text(reply_text)
    return next_step

def find(update: Update, context, regexp, not_found_message: str, table_info: str):
    logging.info("Вызван find. Регулярное выражение: " + regexp + " Сообщение о неудачном поиске: " + not_found_message)
    user_input = update.message.text
    logging.debug(user_input)
    regexp = re.compile(regexp)
    found = regexp.findall(user_input)
    logging.debug(found)
    if not found:
        update.message.reply_text(not_found_message)
        logging.info("Закончен find. Не найдено")
        return ConversationHandler.END
    findings = ''
    global last_regexp_read
    last_regexp_read = []
    for i,finding in enumerate(found):
        findings += f'{i+1}) {"".join(finding)}\n'
        last_regexp_read.append(("".join(finding),))
    logging.debug(findings)
    update.message.reply_text(findings)
    logging.info("Вывод выбора")
    keyboard = [
        [
            InlineKeyboardButton("Да", callback_data=table_info),
            InlineKeyboardButton("Нет", callback_data="Нет")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Добавлять данные в таблицу?', reply_markup=reply_markup)
    logging.info("Закончен find. Найдено")
    return ConversationHandler.END

def verify_password_command(update: Update, context):
    logging.info("Вызван verify_password_command")
    update.message.reply_text('Введите пароль: ')
    return 'verify_password'

def verify_password(update: Update, context):
    logging.info("Вызван verify_password")
    user_input = update.message.text
    logging.debug(user_input)
    password_regexp = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')
    password_test = password_regexp.search(user_input)
    logging.debug(password_test)
    if not password_test:
        update.message.reply_text("Пароль не надёжен")
        logging.info("Закончен verify_password. Пароль не надёжен.")
        return ConversationHandler.END
    update.message.reply_text("Пароль надёжен")
    logging.info("Закончен verify_password. Пароль надёжен.")
    return ConversationHandler.END

def start_command(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Здравствуйте, {user.full_name}. Напишите /help для получения списка команд.')


def help_command(update: Update, context):
    update.message.reply_text(help_message)

def get_ssh_command(update: Update, context, ssh_command: str):
    logging.info("Вызван ssh_command. Команда: " + ssh_command)
    logging.debug(context.args)
    connect = ssh_connect()
    if not connect:
        update.message.reply_text("Доступ к серверу по ssh на данный момент не осуществляется. Но мы уже работаем над этим.")
        logging.info("Завершение ssh_command. Неудача при подключении.")
        return
    if not context.args:
        stdin, stdout, stderr = connect.exec_command(ssh_command)
    else:
        stdin, stdout, stderr = connect.exec_command(ssh_command + " | grep " + context.args[0])
    data_out = stdout.read().decode()
    data_err = stderr.read().decode()
    logging.debug(data_out + data_err)
    for i in range(0,len(data_out),4096):
        update.message.reply_text(data_out[i:i+4096])
    logging.info("Завершение ssh_command.")
    
def psql_select(update: Update, context, table_name: str):
    logging.info("Вызван psql_select с названием таблицы " + table_name)
    connection = None
    try:
        connection = psycopg2.connect(user=PSQL_USERNAME, password=PSQL_PASSWORD, host=PSQL_HOST, port=PSQL_PORT, database="emails_and_phone_numbers")
        cursor = connection.cursor()
        sql_query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(table_name))
        cursor.execute(sql_query)
        data = cursor.fetchall()
        reply = ""
        for row in data:
            reply += f'{row[0]}) {row[1]}\n'
        update.message.reply_text(reply)
        logging.info("Команда успешно выполнена")
    except (Exception, Error) as error:
        logging.error("Ошибка при работе с PostgreSQL: %s", error)
        update.message.reply_text("Произошла ошибка при извлечении данных из таблицы")
    finally:
        if connection is not None:
            cursor.close()
            connection.close()
            logging.info("Соединение с PostgreSQL закрыто")
    return ConversationHandler.END

def psql_insert(update: Update, context):
    query = update.callback_query
    query.answer()
    logging.info("Вызван psql_insert с данными: " + query.data)
    if query.data == "Нет":
        query.message.reply_text("Вы выбрали Нет. Данные не будут записаны в таблицу")
        return
    table_info = json.loads(query.data)
    connection = None
    global last_regexp_read
    logging.debug(last_regexp_read)
    if not last_regexp_read: return 
    try:
        connection = psycopg2.connect(user=PSQL_USERNAME, password=PSQL_PASSWORD, host=PSQL_HOST, port=PSQL_PORT, database=PSQL_DATABASE_NAME)
        cursor = connection.cursor()
        sql_query = sql.SQL("INSERT INTO {} ({}) VALUES (%s);").format(sql.Identifier(table_info['table_name']), sql.Identifier(table_info['column_name']))
        #sql_query = f"INSERT INTO {table_info['table_name']} ({table_info['column_name']}) VALUES (%s);"
        logging.debug("sql_query: " + repr(sql_query))
        cursor.executemany(sql_query, last_regexp_read)
        connection.commit()
        logging.info("Добавление выполено")
        query.message.reply_text("Данные добавлены")
    except (Exception, Error) as error:
        logging.error("Ошибка при работе с PostgreSQL: %s", error)
        query.message.reply_text("Произошла ошибка при добавлении данных в таблицу")
    finally:
        if connection is not None:
            cursor.close()
            connection.close()
            logging.info("Соединение с PostgreSQL закрыто")
    last_regexp_read = []

def get_repl_logs(update: Update, context):
    logging.info("Вызван get_repl_logs")
    output = subprocess.run("cat /app/db_logs/* | grep -i repl", shell=True, capture_output=True, text=True).stdout
    logging.debug(output)
    if not output:
        update.message.reply_text("Логи о репликации не найдены")
        return
    for i in range(0, len(output), 4096):
        update.message.reply_text(output[i:i+4096])

def error_handler(update, context):
    logging.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    logging.info("Начат main")
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    logging.info("Начато добавление команд")
    dp.add_handler(CommandHandler("start", start_command))
    logging.debug("Команда start добавлена")
    dp.add_handler(CommandHandler("help", help_command))
    logging.debug("Команда help добавлена")
    logging.debug("Импорт комманд ssh из json")
    ssh_commands = {}
    try:
        with open("ssh_commands.json", "r") as fp:
            ssh_commands = json.load(fp)
    except Exception as e:
        logging.critical("Ошибка при считывании ssh_commands.json" + repr(e))
    logging.debug("Импорт комманд ssh из json закончен")
    logging.debug(ssh_commands)
    logging.debug("Команды ssh:")
    for telegram_command, linux_comand in ssh_commands.items():
        handler = partial(get_ssh_command, ssh_command = linux_comand)
        dp.add_handler(CommandHandler(telegram_command, handler))
        logging.debug("Добавлена команда " + telegram_command)
    logging.debug("Команды ssh добавлены")
    logging.debug("Импорт комманд regexp из json")
    regexp_commands = {}
    try:
        with open("regexp_commands.json", "r") as fp:
            regexp_commands = json.load(fp)
    except Exception as e:
        logging.critical("Ошибка при считывании regexp_commands.json" + repr(e))
    logging.debug("Импорт комманд regexp из json закончен")
    logging.debug(regexp_commands)
    logging.debug("Команды regexp:")
    for telegram_command, params in regexp_commands.items():
        handler = ConversationHandler(
            entry_points=[CommandHandler(telegram_command, partial(find_command, reply_text = params["reply_text"], next_step = params["next_step"]))],
            states={
                params["next_step"]: [MessageHandler(Filters.text & ~Filters.command, partial(find, regexp = params["regexp"], not_found_message = params["not_found_message"], table_info = json.dumps({"table_name": params["table_name"], "column_name": params["column_name"]})))],
            },
            fallbacks=[]
        )
        dp.add_handler(handler)
        logging.debug("Добавлена команда " + telegram_command)
    logging.debug("Команды regexp добавлены")
    verify_password_handler = ConversationHandler(
        entry_points=[CommandHandler("verify_password", verify_password_command)],
        states={
            "verify_password": [MessageHandler(Filters.text & ~Filters.command, verify_password)],
        },
        fallbacks=[]
    )
    dp.add_handler(verify_password_handler)
    logging.debug("Команда verify_password добавлена")
    logging.debug("Импорт комманд select из json")
    select_commands = {}
    try:
        with open("select_commands.json", "r") as fp:
            select_commands = json.load(fp)
    except Exception as e:
        logging.critical("Ошибка при считывании select_commands.json" + repr(e))
    logging.debug("Импорт комманд select из json закончен")
    logging.debug(select_commands)
    for telegram_command, table_name in select_commands.items():
        handler = partial(psql_select, table_name = table_name)
        dp.add_handler(CommandHandler(telegram_command, handler))
        logging.debug("Добавлена команда " + telegram_command)
    dp.add_handler(CommandHandler("get_repl_logs", get_repl_logs))
    logging.debug("Команда get_repl_logs добавлена")
    logging.info("Команды добавлены")
    logging.info("Добавляем хэндлер нажатия кнопок")
    dp.add_handler(CallbackQueryHandler(psql_insert))
    logging.info("Добавляем хэндлер ошибок")
    dp.add_error_handler(error_handler)
    logging.info("Запускаем бота")
    updater.start_polling()
    logging.info("Бот запущен")
    updater.idle()
    logging.info("Работа завершена")

    
if __name__ == "__main__":
    main()
