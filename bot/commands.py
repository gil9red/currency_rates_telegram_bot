#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


# pip install python-telegram-bot
from telegram import Update, ReplyKeyboardMarkup, ParseMode
from telegram.ext import Dispatcher, MessageHandler, CommandHandler, Filters, CallbackContext

import db
from config import USER_NAME_ADMINS, DEFAULT_CURRENCY_CODE_LIST, DEFAULT_CURRENCY_CODE
from bot.common import get_date_str, log, log_func, process_error, reply_message, SeverityEnum, SubscriptionResultEnum
from utils.graph import get_plot_for_currency


# TODO: переместить в regexp_patterns.py
# TODO: обернуть в регулярки
COMMAND_SUBSCRIBE = 'Подписаться'
COMMAND_UNSUBSCRIBE = 'Отписаться'
COMMAND_LAST = 'Последнее значение'
COMMAND_LAST_BY_WEEK = 'За неделю'
COMMAND_LAST_BY_MONTH = 'За месяц'

FILTER_BY_ADMIN = Filters.user(username=USER_NAME_ADMINS)


def get_reply_keyboard(update: Update):
    is_active = db.Subscription.has_is_active(update.effective_user.id)

    commands = [
        [COMMAND_LAST, COMMAND_LAST_BY_WEEK, COMMAND_LAST_BY_MONTH],
        [COMMAND_UNSUBSCRIBE if is_active else COMMAND_SUBSCRIBE]
    ]
    return ReplyKeyboardMarkup(commands, resize_keyboard=True)


@log_func(log)
def on_start(update: Update, context: CallbackContext):
    reply_message(
        f'Приветсвую {update.effective_user.first_name} 🙂\n'
        'Данный бот способен отслеживать валюты и отправлять вам уведомление при изменении 💲.\n'
        'С помощью меню вы можете подписаться/отписаться от рассылки, узнать '
        'актуальный курс за день, неделю или месяц.',
        update=update, context=context,
        parse_mode=ParseMode.HTML,
        reply_markup=get_reply_keyboard(update),
    )


@log_func(log)
def on_get_admin_stats(update: Update, context: CallbackContext):
    currency_count = db.ExchangeRate.select().count()
    first_date = get_date_str(db.ExchangeRate.select().first().date)
    last_date = get_date_str(db.ExchangeRate.get_last().date)

    subscription_active_count = db.Subscription.select().where(db.Subscription.is_active == True).count()

    reply_message(
        f'<b>Статистика админа</b>\n\n'
        f'<b>Курсы валют</b>\n'
        f'Количество: <b><u>{currency_count}</u></b>\n'
        f'Диапазон значений: <b><u>{first_date} - {last_date}</u></b>\n\n'
        f'<b>Подписки</b>\n'
        f'Количество активных: <b><u>{subscription_active_count}</u></b>',
        update=update, context=context,
        parse_mode=ParseMode.HTML,
        severity=SeverityEnum.INFO,
        reply_markup=get_reply_keyboard(update)
    )


@log_func(log)
def on_command_subscribe(update: Update, context: CallbackContext):
    message = update.effective_message
    user_id = message.from_user.id

    result = db.Subscription.subscribe(user_id)
    match result:
        case SubscriptionResultEnum.ALREADY:
            text = 'Подписка уже оформлена 🤔!'
        case SubscriptionResultEnum.SUBSCRIBE_OK:
            text = 'Подписка успешно оформлена 😉!'
        case _:
            raise Exception(f'Неожиданный результат {result} для метода "subscribe"!')

    reply_message(
        text=text,
        update=update, context=context,
        severity=SeverityEnum.INFO,
        reply_markup=get_reply_keyboard(update),
    )


@log_func(log)
def on_command_unsubscribe(update: Update, context: CallbackContext):
    message = update.effective_message
    user_id = message.from_user.id

    result = db.Subscription.unsubscribe(user_id)
    match result:
        case SubscriptionResultEnum.ALREADY:
            text = 'Подписка не оформлена 🤔!'
        case SubscriptionResultEnum.UNSUBSCRIBE_OK:
            text = 'Вы успешно отписались 😔'
        case _:
            raise Exception(f'Неожиданный результат {result} для метода "unsubscribe"!')

    reply_message(
        text=text,
        update=update, context=context,
        severity=SeverityEnum.INFO,
        reply_markup=get_reply_keyboard(update),
    )


@log_func(log)
def on_command_last(update: Update, context: CallbackContext):
    # TODO: Default currency code? Или мб брать первую валюту из настроек?
    reply_message(
        text=db.ExchangeRate.get_full_description(DEFAULT_CURRENCY_CODE_LIST),
        update=update, context=context,
        parse_mode=ParseMode.HTML,
        reply_markup=get_reply_keyboard(update)
    )


@log_func(log)
def on_command_last_by_week(update: Update, context: CallbackContext):
    currency_code = DEFAULT_CURRENCY_CODE
    number = 7

    # TODO: Default currency code? Или мб брать первую валюту из настроек?
    reply_message(
        text='',
        photo=get_plot_for_currency(
            currency_code=currency_code,
            number=number,
        ),
        update=update, context=context,
        parse_mode=ParseMode.HTML,
        reply_markup=get_reply_keyboard(update)
    )


@log_func(log)
def on_command_last_by_month(update: Update, context: CallbackContext):
    currency_code = DEFAULT_CURRENCY_CODE
    number = 30

    # TODO: Default currency code? Или мб брать первую валюту из настроек?
    reply_message(
        text='',
        photo=get_plot_for_currency(
            currency_code=currency_code,
            number=number,
        ),
        update=update, context=context,
        parse_mode=ParseMode.HTML,
        reply_markup=get_reply_keyboard(update)
    )


@log_func(log)
def on_request(update: Update, context: CallbackContext):
    reply_message(
        'Неизвестная команда 🤔',
        update=update, context=context,
        reply_markup=get_reply_keyboard(update)
    )


def on_error(update: Update, context: CallbackContext):
    process_error(log, update, context)


def setup(dp: Dispatcher):
    dp.add_handler(CommandHandler('start', on_start))

    dp.add_handler(CommandHandler('admin_stats', on_get_admin_stats, FILTER_BY_ADMIN))
    # TODO: В переменную
    dp.add_handler(MessageHandler(Filters.text('Статистика админа') & FILTER_BY_ADMIN, on_get_admin_stats))

    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST), on_command_last))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST_BY_WEEK), on_command_last_by_week))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST_BY_MONTH), on_command_last_by_month))

    dp.add_handler(MessageHandler(Filters.text(COMMAND_SUBSCRIBE), on_command_subscribe))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_UNSUBSCRIBE), on_command_unsubscribe))

    dp.add_handler(MessageHandler(Filters.text, on_request))

    dp.add_error_handler(on_error)
