#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import datetime as DT
import enum
import functools
import json
import inspect
import logging
import sys

from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Union, Optional

from telegram import Update, ReplyMarkup, InlineKeyboardMarkup, CallbackQuery, Message
from telegram.error import NetworkError, BadRequest
from telegram.ext import CallbackContext
from telegram.utils.types import FileInput
from telegram.files.photosize import PhotoSize

from root_config import DATE_FORMAT, DIR_LOGS, ERROR_TEXT, MAX_MESSAGE_LENGTH


def get_start_date(year: int) -> DT.date:
    return DT.date(year, 1, 1)


def get_end_date(year: int) -> DT.date:
    return DT.date(year + 1, 1, 1) - DT.timedelta(days=1)


def get_date_str(date: DT.date) -> str:
    return date.strftime(DATE_FORMAT)


def caller_name() -> str:
    """Return the calling function's name."""
    return inspect.currentframe().f_back.f_code.co_name


def get_logger(
        name: str,
        file: Union[str, Path] = 'log.txt',
        encoding='utf-8',
        log_stdout=True,
        log_file=True
) -> 'logging.Logger':
    log = logging.getLogger(name)

    # Возвращаем уже существующий логгер
    if log.handlers:
        return log

    log.setLevel(logging.DEBUG)

    formatter = logging.Formatter('[%(asctime)s] %(filename)s:%(lineno)d %(levelname)-8s %(message)s')

    if log_file:
        fh = RotatingFileHandler(file, maxBytes=10000000, backupCount=5, encoding=encoding)
        fh.setFormatter(formatter)
        log.addHandler(fh)

    if log_stdout:
        sh = logging.StreamHandler(stream=sys.stdout)
        sh.setFormatter(formatter)
        log.addHandler(sh)

    return log


def log_func(log: logging.Logger):
    def actual_decorator(func):
        @functools.wraps(func)
        def wrapper(update: Update, context: CallbackContext):
            if update:
                chat_id = user_id = first_name = last_name = username = language_code = None

                if update.effective_chat:
                    chat_id = update.effective_chat.id

                if update.effective_user:
                    user_id = update.effective_user.id
                    first_name = update.effective_user.first_name
                    last_name = update.effective_user.last_name
                    username = update.effective_user.username
                    language_code = update.effective_user.language_code

                try:
                    message = update.effective_message.text
                except:
                    message = ''

                try:
                    query_data = update.callback_query.data
                except:
                    query_data = ''

                msg = f'[chat_id={chat_id}, user_id={user_id}, ' \
                      f'first_name={first_name!r}, last_name={last_name!r}, ' \
                      f'username={username!r}, language_code={language_code}, ' \
                      f'message={message!r}, query_data={query_data!r}]'
                msg = func.__name__ + msg

                log.debug(msg)

            return func(update, context)

        return wrapper
    return actual_decorator


class SeverityEnum(enum.Enum):
    NONE = '{text}'
    INFO = 'ℹ️ {text}'
    ERROR = '⚠ {text}'

    def get_text(self, text: str) -> str:
        return self.value.format(text=text)


# SOURCE: https://github.com/gil9red/get_metal_rates/blob/6483005419c6abde470763af0b750159c1cc1290/root_common.py#L53
class SubscriptionResultEnum(enum.Enum):
    SUBSCRIBE_OK = enum.auto()
    UNSUBSCRIBE_OK = enum.auto()
    ALREADY = enum.auto()


def reply_message(
        text: str,
        update: Update,
        context: CallbackContext,
        photo: Union[FileInput, PhotoSize] = None,
        severity: SeverityEnum = SeverityEnum.NONE,
        reply_markup: ReplyMarkup = None,
        quote: bool = True,
        **kwargs
):
    message = update.effective_message

    text = severity.get_text(text)

    if photo:
        # Для фото не будет разделения сообщения на куски
        mess = text[:MAX_MESSAGE_LENGTH]
        message.reply_photo(
            photo=photo,
            caption=mess,
            reply_markup=reply_markup,
            quote=quote,
            **kwargs
        )
    else:
        for n in range(0, len(text), MAX_MESSAGE_LENGTH):
            mess = text[n: n + MAX_MESSAGE_LENGTH]
            message.reply_text(
                mess,
                reply_markup=reply_markup,
                quote=quote,
                **kwargs
            )


# SOURCE: https://github.com/gil9red/get_metal_rates/blob/1f43cf779cd34753654cbc2681a408352fa37709/app_tg_bot/bot/common.py#L234
def is_equal_inline_keyboards(
        keyboard_1: Union[InlineKeyboardMarkup, str],
        keyboard_2: InlineKeyboardMarkup
) -> bool:
    if isinstance(keyboard_1, InlineKeyboardMarkup):
        keyboard_1_inline_keyboard = keyboard_1.to_dict()['inline_keyboard']
    elif isinstance(keyboard_1, str):
        keyboard_1_inline_keyboard = json.loads(keyboard_1)['inline_keyboard']
    else:
        raise Exception(f'Unsupported format (keyboard_1={type(keyboard_1)})!')

    keyboard_2_inline_keyboard = keyboard_2.to_dict()['inline_keyboard']
    return keyboard_1_inline_keyboard == keyboard_2_inline_keyboard


# SOURCE: https://github.com/gil9red/telegram__random_bashim_bot/blob/e9c98248f10c4a74f0e26dcf5a949bf2260f57d4/common.py#L177
def reply_text_or_edit_with_keyboard(
    message: Message,
    query: Optional[CallbackQuery],
    text: str,
    reply_markup: Union[InlineKeyboardMarkup, str],
    quote: bool = True,
    **kwargs,
):
    # Для запросов CallbackQuery нужно менять текущее сообщение
    if query:
        # Fix error: "telegram.error.BadRequest: Message is not modified"
        if text == query.message.text and is_equal_inline_keyboards(reply_markup, query.message.reply_markup):
            return

        try:
            message.edit_text(
                text,
                reply_markup=reply_markup,
                **kwargs,
            )
        except BadRequest as e:
            if 'Message is not modified' in str(e):
                return

            raise e

    else:
        message.reply_text(
            text,
            reply_markup=reply_markup,
            quote=quote,
            **kwargs,
        )


def process_error(log: logging.Logger, update: Update, context: CallbackContext):
    log.error('Error: %s\nUpdate: %s', context.error, update, exc_info=context.error)
    if update:
        # Не отправляем ошибку пользователю при проблемах с сетью (типа, таймаут)
        if isinstance(context.error, NetworkError):
            return

        reply_message(ERROR_TEXT, update, context, severity=SeverityEnum.ERROR)


log = get_logger(__file__, DIR_LOGS / 'log.txt')
