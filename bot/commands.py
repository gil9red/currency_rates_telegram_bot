#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


# pip install python-telegram-bot
from telegram import Update, ReplyKeyboardMarkup, ParseMode
from telegram.ext import Dispatcher, MessageHandler, CommandHandler, Filters, CallbackContext

import db
from config import USER_NAME_ADMINS, PATH_GRAPH_WEEK, PATH_GRAPH_MONTH
from bot.common import get_date_str, log, log_func, process_error


COMMAND_SUBSCRIBE = 'Подписаться'
COMMAND_UNSUBSCRIBE = 'Отписаться'
COMMAND_LAST = 'Последнее значение'
COMMAND_LAST_BY_WEEK = 'За неделю'
COMMAND_LAST_BY_MONTH = 'За месяц'

FILTER_BY_ADMIN = Filters.user(username=USER_NAME_ADMINS)


def get_keyboard(update):
    is_active = db.Subscription.get_is_active(update.effective_chat.id)

    commands = [
        [COMMAND_LAST, COMMAND_LAST_BY_WEEK, COMMAND_LAST_BY_MONTH],
        [COMMAND_UNSUBSCRIBE if is_active else COMMAND_SUBSCRIBE]
    ]
    return ReplyKeyboardMarkup(commands, resize_keyboard=True)


@log_func(log)
def on_start(update: Update, context: CallbackContext):
    update.effective_message.reply_html(
        f'Приветсвую {update.effective_user.first_name} 🙂\n'
        'Данный бот способен отслеживать USD валюту и отправлять вам уведомление при изменении 💲.\n'
        'С помощью меню вы можете подписаться/отписаться от рассылки, узнать актуальный курс за день, неделю или месяц.',
        reply_markup=get_keyboard(update)
    )


@log_func(log)
def on_get_admin_stats(update: Update, context: CallbackContext):
    currency_count = db.ExchangeRate.select().count()
    first_date = get_date_str(db.ExchangeRate.select().first().date)
    last_date = get_date_str(db.ExchangeRate.get_last().date)

    subscription_active_count = db.Subscription.select().where(db.Subscription.is_active == True).count()

    update.effective_message.reply_html(
        f'<b>Статистика админа</b>\n\n'
        f'<b>Курсы валют</b>\nКоличество: <b><u>{currency_count}</u></b>\nДиапазон значений: <b><u>{first_date} - {last_date}</u></b>\n\n'
        f'<b>Подписки</b>\nКоличество активных: <b><u>{subscription_active_count}</u></b>',
        reply_markup=get_keyboard(update)
    )


@log_func(log)
def on_command_subscribe(update: Update, context: CallbackContext):
    message = update.effective_message

    user = db.Subscription.select().where(db.Subscription.chat_id == update.effective_chat.id)

    if not user:
        db.Subscription.create(chat_id=update.effective_chat.id)
        message.text = "Вы успешно подписались 😉"
    else:
        if user.get().is_active:
            message.text = "Подписка уже оформлена 🤔"
        else:
            db.Subscription.set_active(user.get(), True)

            message.text = "Вы успешно подписались 😉"

    message.reply_html(
        message.text,
        reply_markup=get_keyboard(update)
    )


@log_func(log)
def on_command_unsubscribe(update: Update, context: CallbackContext):
    message = update.effective_message

    user = db.Subscription.get_is_active(update.effective_chat.id)

    if user:
        db.Subscription.set_active(user, False)

        message.text = "Вы успешно отписались 😔"
    else:
        message.text = "Подписка не оформлена 🤔"

    message.reply_html(
        message.text,
        reply_markup=get_keyboard(update)
    )


@log_func(log)
def on_command_last(update: Update, context: CallbackContext):
    if db.ExchangeRate.select().first():
        update.effective_message.reply_html(
            f'Актуальный курс USD за <b><u>{get_date_str(db.ExchangeRate.get_last().date)}</u></b>: '
            f'{db.ExchangeRate.get_last().value}₽',
            reply_markup=get_keyboard(update)
        )
    else:
        update.effective_message.reply_html(
            'Бот не имеет достаточно информации 😔',
            reply_markup=get_keyboard(update)
        )


@log_func(log)
def on_command_last_by_week(update: Update, context: CallbackContext):
    message = update.effective_message

    items = [x.value for x in db.ExchangeRate.get_last_by(days=7)]
    if items:
        message.reply_photo(
            open(PATH_GRAPH_WEEK, 'rb'),
            f'Среднее USD за <b><u>неделю</u></b>: {sum(items) / len(items):.2f}₽',
            parse_mode=ParseMode.HTML,
            reply_markup=get_keyboard(update)
        )
    else:
        message.reply_html(
            'Бот не имеет достаточно информации 😔',
            reply_markup=get_keyboard(update)
        )


@log_func(log)
def on_command_last_by_month(update: Update, context: CallbackContext):
    message = update.effective_message

    items = [x.value for x in db.ExchangeRate.get_last_by(days=30)]
    if items:
        message.reply_photo(
            open(PATH_GRAPH_MONTH, 'rb'),
            f'Среднее USD за <b><u>месяц</u></b>: {sum(items) / len(items):.2f}₽',
            parse_mode=ParseMode.HTML,
            reply_markup=get_keyboard(update)
        )
    else:
        message.reply_html(
            'Бот не имеет достаточно информации 😔',
            reply_markup=get_keyboard(update)
        )


@log_func(log)
def on_request(update: Update, context: CallbackContext):
    update.effective_message.reply_html(
        'Неизвестная команда 🤔',
        reply_markup=get_keyboard(update)
    )


def on_error(update: Update, context: CallbackContext):
    process_error(log, update, context)


def setup(dp: Dispatcher):
    dp.add_handler(CommandHandler('start', on_start))

    dp.add_handler(CommandHandler('admin_stats', on_get_admin_stats, FILTER_BY_ADMIN))
    # TODO: В переменную
    dp.add_handler(MessageHandler(Filters.text('Статистика админа') and FILTER_BY_ADMIN, on_get_admin_stats))

    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST), on_command_last))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST_BY_WEEK), on_command_last_by_week))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST_BY_MONTH), on_command_last_by_month))

    dp.add_handler(MessageHandler(Filters.text(COMMAND_SUBSCRIBE), on_command_subscribe))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_UNSUBSCRIBE), on_command_unsubscribe))

    dp.add_handler(MessageHandler(Filters.text, on_request))

    dp.add_error_handler(on_error)
