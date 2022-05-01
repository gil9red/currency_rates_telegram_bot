#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import datetime as DT

# pip install python-telegram-bot
from telegram import Update, ReplyKeyboardMarkup, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Dispatcher, MessageHandler, CommandHandler, Filters, CallbackContext, CallbackQueryHandler

import db
from root_config import USER_NAME_ADMINS, DEFAULT_CURRENCY_CODES, DEFAULT_CURRENCY_CODE
from bot.common import get_date_str, log, log_func, process_error, reply_message, SeverityEnum, SubscriptionResultEnum
from bot.regexp_patterns import (
    PATTERN_INLINE_GET_BY_DATE, COMMAND_SUBSCRIBE, COMMAND_UNSUBSCRIBE,
    COMMAND_LAST, COMMAND_LAST_BY_WEEK, COMMAND_LAST_BY_MONTH, COMMAND_GET_ALL,
    COMMAND_ADMIN_STATS, REPLY_ADMIN_STATS,
    fill_string_pattern,
)
from utils.graph import get_plot_for_currency


FILTER_BY_ADMIN = Filters.user(username=USER_NAME_ADMINS)


def get_reply_keyboard(update: Update) -> ReplyKeyboardMarkup:
    is_active = db.Subscription.has_is_active(update.effective_user.id)

    commands = [
        [COMMAND_LAST],
        [COMMAND_LAST_BY_WEEK, COMMAND_LAST_BY_MONTH, COMMAND_GET_ALL],
        [COMMAND_UNSUBSCRIBE if is_active else COMMAND_SUBSCRIBE]
    ]
    return ReplyKeyboardMarkup(commands, resize_keyboard=True)


# SOURCE: https://github.com/gil9red/get_metal_rates/blob/0f3c38bc4fc287504173471aefdaeb0e5e1ae98d/app_tg_bot/bot/commands.py#L48
def get_inline_keyboard_for_date_pagination(for_date: DT.date) -> InlineKeyboardMarkup:
    prev_date, next_date = db.ExchangeRate.get_prev_next_dates(for_date)

    prev_date_str = f'❮ {get_date_str(prev_date)}' if prev_date else ''
    prev_date_callback_data = fill_string_pattern(PATTERN_INLINE_GET_BY_DATE, prev_date if prev_date else '')

    next_date_str = f'{get_date_str(next_date)} ❯' if next_date else ''
    next_date_callback_data = fill_string_pattern(PATTERN_INLINE_GET_BY_DATE, next_date if next_date else '')

    return InlineKeyboardMarkup.from_row([
        InlineKeyboardButton(text=prev_date_str, callback_data=prev_date_callback_data),
        InlineKeyboardButton(text=next_date_str, callback_data=next_date_callback_data),
    ])


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
def on_command_last(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        query.answer()

    try:
        for_date: DT.date = DT.date.fromisoformat(context.match.group(1))
    except:
        for_date: DT.date = db.ExchangeRate.get_last_date()

    # TODO: Default currency code? Или мб брать первую валюту из настроек?
    text = db.ExchangeRate.get_full_description(DEFAULT_CURRENCY_CODES, for_date)

    reply_message(
        text=text,
        update=update, context=context,
        parse_mode=ParseMode.HTML,
        reply_markup=get_inline_keyboard_for_date_pagination(for_date)
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
def on_command_get_all(update: Update, context: CallbackContext):
    currency_code = DEFAULT_CURRENCY_CODE
    number = -1

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

    dp.add_handler(CommandHandler(COMMAND_ADMIN_STATS, on_get_admin_stats, FILTER_BY_ADMIN))
    dp.add_handler(MessageHandler(Filters.text(REPLY_ADMIN_STATS) & FILTER_BY_ADMIN, on_get_admin_stats))

    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST), on_command_last))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST_BY_WEEK), on_command_last_by_week))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST_BY_MONTH), on_command_last_by_month))

    dp.add_handler(MessageHandler(Filters.text(COMMAND_GET_ALL), on_command_get_all))
    dp.add_handler(CallbackQueryHandler(on_command_get_all, pattern=PATTERN_INLINE_GET_BY_DATE))

    dp.add_handler(MessageHandler(Filters.text(COMMAND_SUBSCRIBE), on_command_subscribe))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_UNSUBSCRIBE), on_command_unsubscribe))

    dp.add_handler(MessageHandler(Filters.text, on_request))

    dp.add_error_handler(on_error)
