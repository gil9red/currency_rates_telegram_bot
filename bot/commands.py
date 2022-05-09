#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import datetime as DT

# pip install python-telegram-bot
from telegram import (
    Update, ReplyKeyboardMarkup, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ReplyMarkup, InputMediaPhoto
)
from telegram.error import BadRequest
from telegram.ext import Dispatcher, MessageHandler, CommandHandler, Filters, CallbackContext, CallbackQueryHandler

import db
from root_config import USER_NAME_ADMINS, DEFAULT_CURRENCY_CODES, DEFAULT_CURRENCY_CODE
from bot.common import (
    log, log_func, process_error, reply_message, reply_text_or_edit_with_keyboard,
    SeverityEnum, SubscriptionResultEnum, is_equal_inline_keyboards
)
from root_common import get_date_str
from bot.regexp_patterns import (
    PATTERN_INLINE_GET_BY_DATE, COMMAND_SUBSCRIBE, COMMAND_UNSUBSCRIBE,
    COMMAND_LAST, COMMAND_LAST_BY_WEEK, COMMAND_LAST_BY_MONTH, COMMAND_GET_ALL,
    COMMAND_ADMIN_STATS, REPLY_ADMIN_STATS,
    PATTERN_REPLY_SELECT_DATE, PATTERN_INLINE_SELECT_DATE,
    PATTERN_INLINE_GET_CHART_CURRENCY_BY_YEAR,
    CALLBACK_IGNORE,
    fill_string_pattern,
)
from bot.third_party.auto_in_progress_message import show_temp_message_decorator, ProgressValue
from bot.third_party import telegramcalendar

from utils.graph import get_plot_for_currency


FILTER_BY_ADMIN = Filters.user(username=USER_NAME_ADMINS)

TEXT_SHOW_TEMP_MESSAGE = SeverityEnum.INFO.get_text('Пожалуйста, подождите {value}')
PROGRESS_VALUE = ProgressValue.RECTS_SMALL

FORMAT_PREV = '❮ {}'
FORMAT_CURRENT = '· {} ·'
FORMAT_NEXT = '{} ❯'


def get_inline_keyboard_for_date_pagination(for_date: DT.date) -> InlineKeyboardMarkup:
    pattern = PATTERN_INLINE_GET_BY_DATE
    prev_date, next_date = db.ExchangeRate.get_prev_next_dates(for_date)

    buttons = []
    if prev_date:
        buttons.append(
            InlineKeyboardButton(
                text=FORMAT_PREV.format(get_date_str(prev_date)),
                callback_data=fill_string_pattern(pattern, prev_date),
            )
        )

    # Текущий выбор
    buttons.append(
        InlineKeyboardButton(
            text=FORMAT_CURRENT.format(get_date_str(for_date)),
            callback_data=fill_string_pattern(pattern, CALLBACK_IGNORE),
        )
    )

    if next_date:
        buttons.append(
            InlineKeyboardButton(
                text=FORMAT_NEXT.format(get_date_str(next_date)),
                callback_data=fill_string_pattern(pattern, next_date),
            )
        )

    return InlineKeyboardMarkup.from_row(buttons)


def get_inline_keyboard_for_year_pagination(year: int, currency_code: str) -> InlineKeyboardMarkup:
    pattern = PATTERN_INLINE_GET_CHART_CURRENCY_BY_YEAR
    prev_year, next_year = db.ExchangeRate.get_prev_next_years(year=year, currency_code=currency_code)

    buttons = []
    if prev_year:
        buttons.append(
            InlineKeyboardButton(
                text=FORMAT_PREV.format(prev_year),
                callback_data=fill_string_pattern(pattern, currency_code, prev_year),
            )
        )

    # Текущий выбор
    buttons.append(
        InlineKeyboardButton(
            text=FORMAT_CURRENT.format(year),
            callback_data=fill_string_pattern(pattern, CALLBACK_IGNORE, CALLBACK_IGNORE),
        )
    )

    if next_year:
        buttons.append(
            InlineKeyboardButton(
                text=FORMAT_NEXT.format(next_year),
                callback_data=fill_string_pattern(pattern, currency_code, next_year)
            )
        )

    return InlineKeyboardMarkup.from_row(buttons)


def get_reply_keyboard(update: Update) -> ReplyKeyboardMarkup:
    is_active = db.Subscription.has_is_active(update.effective_user.id)

    commands = [
        [COMMAND_LAST, fill_string_pattern(PATTERN_REPLY_SELECT_DATE)],
        [COMMAND_LAST_BY_WEEK, COMMAND_LAST_BY_MONTH, COMMAND_GET_ALL],
        [COMMAND_UNSUBSCRIBE if is_active else COMMAND_SUBSCRIBE]
    ]
    return ReplyKeyboardMarkup(commands, resize_keyboard=True)


def reply_or_edit_plot_with_keyboard(
    update: Update,
    currency_code: str,
    number: int = -1,
    year: int = None,
    title: str = '',
    reply_markup: ReplyMarkup = None,
    quote: bool = True,
    **kwargs,
):
    message = update.effective_message
    query = update.callback_query

    photo = get_plot_for_currency(
        currency_code=currency_code,
        number=number,
        year=year,
    )

    # Для запросов CallbackQuery нужно менять текущее сообщение
    if query:
        # Fix error: "telegram.error.BadRequest: Message is not modified"
        if reply_markup and is_equal_inline_keyboards(reply_markup, query.message.reply_markup):
            return

        try:
            message.edit_media(
                media=InputMediaPhoto(media=photo, caption=title),
                reply_markup=reply_markup,
                **kwargs,
            )
        except BadRequest as e:
            if 'Message is not modified' in str(e):
                return

            raise e

    else:
        message.reply_photo(
            photo=photo,
            caption=title,
            reply_markup=reply_markup,
            quote=quote,
            **kwargs,
        )


@log_func(log)
def on_start(update: Update, context: CallbackContext):
    reply_message(
        f'Приветствую {update.effective_user.first_name} 🙂\n'
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
    message = update.effective_message

    query = update.callback_query
    if query:
        query.answer()

    try:
        value: str = context.match.group(1)
        if value == CALLBACK_IGNORE:
            return

        for_date: DT.date = DT.date.fromisoformat(value)
    except:
        for_date: DT.date = db.ExchangeRate.get_last_date()

    # TODO: Default currency code? Или мб брать первую валюту из настроек?
    text = db.ExchangeRate.get_full_description(DEFAULT_CURRENCY_CODES, for_date)

    reply_text_or_edit_with_keyboard(
        message=message, query=query,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_inline_keyboard_for_date_pagination(for_date)
    )


@log_func(log)
def on_select_date(update: Update, context: CallbackContext):
    query = update.callback_query
    if not query:
        date = db.ExchangeRate.get_last_date()
        reply_message(
            "Пожалуйста, выберите дату:",
            update=update, context=context,
            reply_markup=telegramcalendar.create_calendar(
                year=date.year,
                month=date.month
            )
        )
        return

    query.answer()

    bot = context.bot

    selected, for_date = telegramcalendar.process_calendar_selection(bot, update)
    if selected:
        msg_not_found_for_date = ''
        if not db.ExchangeRate.has_date(for_date):
            msg_not_found_for_date = SeverityEnum.INFO.get_text(
                f'За {get_date_str(for_date)} нет данных, будет выбрана ближайшая дата'
            )
            prev_date, next_date = db.ExchangeRate.get_prev_next_dates(for_date)
            for_date = next_date if next_date else prev_date

        text = db.ExchangeRate.get_full_description(DEFAULT_CURRENCY_CODES, for_date)
        if msg_not_found_for_date:
            text = msg_not_found_for_date + '\n\n' + text

        reply_text_or_edit_with_keyboard(
            message=update.effective_message,
            query=query,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_inline_keyboard_for_date_pagination(for_date),
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
@show_temp_message_decorator(
    text=TEXT_SHOW_TEMP_MESSAGE,
    progress_value=PROGRESS_VALUE,
)
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
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                text='Посмотреть за определенный год',
                callback_data=fill_string_pattern(PATTERN_INLINE_GET_CHART_CURRENCY_BY_YEAR, currency_code, -1)
            )
        ),
    )


@log_func(log)
def on_get_all_by_year(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        query.answer()

    currency_code: str = context.match.group(1)
    if currency_code == CALLBACK_IGNORE:
        return

    year: int = int(context.match.group(2))
    if year == -1:
        year = db.ExchangeRate.get_last_date().year

    reply_or_edit_plot_with_keyboard(
        update=update,
        currency_code=currency_code,
        year=year,
        title=f"Стоимость {currency_code} в рублях за {year}",
        # TODO: Возможность указывать другие валюты из настроек юзера
        reply_markup=get_inline_keyboard_for_year_pagination(
            year=year,
            currency_code=currency_code,
        ),
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
    dp.add_handler(CallbackQueryHandler(on_command_last, pattern=PATTERN_INLINE_GET_BY_DATE))

    dp.add_handler(MessageHandler(Filters.regex(PATTERN_REPLY_SELECT_DATE), on_select_date))
    dp.add_handler(CallbackQueryHandler(on_select_date, pattern=PATTERN_INLINE_SELECT_DATE))

    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST_BY_WEEK), on_command_last_by_week))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_LAST_BY_MONTH), on_command_last_by_month))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_GET_ALL), on_command_get_all))

    dp.add_handler(CallbackQueryHandler(on_get_all_by_year, pattern=PATTERN_INLINE_GET_CHART_CURRENCY_BY_YEAR))

    dp.add_handler(MessageHandler(Filters.text(COMMAND_SUBSCRIBE), on_command_subscribe))
    dp.add_handler(MessageHandler(Filters.text(COMMAND_UNSUBSCRIBE), on_command_unsubscribe))

    dp.add_handler(MessageHandler(Filters.text, on_request))

    dp.add_error_handler(on_error)
