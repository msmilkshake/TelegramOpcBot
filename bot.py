import logging
import os
import random
import re
import sys
import json

from telegram.ext import Updater, CommandHandler
from datetime import datetime, timedelta
# Enabling logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# Getting mode, so we could define run function for local and Heroku setup
mode = os.getenv("MODE")
TOKEN = os.getenv("TOKEN")
if mode == "dev":
    def run(updater):
        updater.start_polling()
elif mode == "prod":
    def run(updater):
        PORT = int(os.environ.get("PORT", "8443"))
        HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")
        # Code from https://github.com/python-telegram-bot/python-telegram-bot/wiki/Webhooks#heroku
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=TOKEN)
        updater.bot.set_webhook("https://{}.herokuapp.com/{}".format(HEROKU_APP_NAME, TOKEN))
else:
    logger.error("No MODE specified!")
    sys.exit(1)


class Officer:
    def __init__(self, uid, name, time):
        self.uid = uid
        self.name = name
        self.time = time

country_data = {}
on_duty = {}


def start_handler(update, context):
    # Creating a handler-function for /start command
    logger.info("User {} started bot".format(update.effective_user["id"]))
    update.message.reply_text('I am now at your service! 💪')


def test_handler(update, context):
    for arg in context.args:
        update.message.reply_text(arg)


def tag_user(update, context):
    uid = update.message.from_user.id
    name = update.message.from_user.username
    print(uid)
    txt = f'[@{name}](tg://user?id={uid})'
    cid = update.effective_chat.id
    context.bot.send_message(chat_id=cid, text=txt, parse_mode='MarkdownV2')


def online_handler(update, context):
    print("in on")
    args = context.args
    if len(args) != 2 or not re.match('\\w\\w\\w?\\w?', args[0]) or not re.match('[1-9]\\d?', args[1]):
        cid = update.effective_chat.id
        txt = 'Invalid command format.'
        context.bot.send_message(chat_id=cid, text=txt)
        return

    uid = update.message.from_user.id
    name = update.message.from_user.username
    nick = update.message.from_user.first_name
    country = context.args[0].upper()

    if country not in country_data['initials'].keys():
        cid = update.effective_chat.id
        txt = 'Invalid country. Use /list to get a list of valid country initials.'
        context.bot.send_message(chat_id=cid, text=txt)
        return

    country = country_data['initials'][country]
    time = int(context.args[1])
    time = datetime.now() + timedelta(hours=time)
    officer = Officer(uid, name, time)
    if country not in on_duty:
        on_duty[country] = {}
    on_duty[country][uid] = officer
    cid = update.effective_chat.id
    key = country_data['initials'][country]
    country_name = country_data['name'][key]
    f1 = int(country_data['flag'][key][:8], base=16)
    f2 = int(country_data['flag'][key][8:], base=16)
    str_time = time.strftime('%d/%m/%Y - %H:%M:%S')
    txt = f'Watch out, {nick} is on patrol for {chr(f1)}{chr(f2)} {country_name} until {str_time}.'
    context.bot.send_message(chat_id=cid, text=txt)


def check_handler(update, context):
    print("in check")
    args = context.args
    if len(args) == 1:
        update_on_duty()
        country = args[0].upper()

        if country not in country_data['initials'].keys():
            cid = update.effective_chat.id
            txt = 'Invalid country. Use /list to get a list of valid country initials.'
            context.bot.send_message(chat_id=cid, text=txt)
            return

        country = country_data['initials'][country]

        country_dict = on_duty.get(country, {})
        if len(country_dict) > 0:
            display_available(country, country_dict, update, context)
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'No one available for {country}',
                                     parse_mode='MarkdownV2')


def update_on_duty():
    for country in list(on_duty):
        country_dict = on_duty[country]
        for key in list(country_dict):
            if country_dict[key].time < datetime.now():
                on_duty.get(country).pop(key)
        if len(country_dict) == 0:
            on_duty.pop(country)


def list_handler(update, context):
    msg = 'List of countries:\n'
    initials = {}
    for key in country_data['initials']:
        initial = country_data['initials'][key]
        if initial not in initials:
            initials[initial] = []
        initials[initial].append(key)
    for key in initials:
        if len(initials[key][0]) > len(initials[key][1]):
            initials[key] = reversed(initials[key])
    for key in sorted(initials):
        words = initials[key]
        name = country_data['name'][key]
        f1 = int(country_data['flag'][key][:8], base=16)
        f2 = int(country_data['flag'][key][8:], base=16)
        msg += f'{words[0]}, {words[1]} - {chr(f1)}{chr(f2)} {name}\n'
    try:
        context.bot.send_message(chat_id=update.message.from_user.id, text=msg)
    except:
        info = 'To avoid spam, talk to me in private and press "Start". Then, repeat the /list command here. 😉'
        context.bot.send_message(chat_id=update.effective_chat.id, text=info)
    ...


def display_available(country, country_dict, update, context):
    f1 = int(country_data['flag'][country][:8], base=16)
    f2 = int(country_data['flag'][country][8:], base=16)
    c_name = country_data['name'][country]
    msg = f'{chr(f1)}{chr(f2)} {c_name} officers on duty:\n'
    print(msg)
    for key in country_dict:
        name = country_dict[key].name
        msg += f'@{name}\n'

    if len(country_dict) != 0:
        context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


if __name__ == '__main__':
    data_file = open('data_file.json', 'r')
    country_data = json.load(data_file)
    data_file.close()
    #json.dump(country_data, data_file, indent=4)

    logger.info("Starting bot")
    updater = Updater(TOKEN)

    updater.dispatcher.add_handler(CommandHandler("start", start_handler))
    updater.dispatcher.add_handler(CommandHandler("on", online_handler, pass_args=True))
    updater.dispatcher.add_handler(CommandHandler("check", check_handler, pass_args=True))
    updater.dispatcher.add_handler(CommandHandler("list", list_handler))

    run(updater)