#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import enum
import functools
import threading
import time

from itertools import cycle

# pip install python-telegram-bot
from telegram import Update, ReplyMarkup, Message, ParseMode
from telegram.ext import CallbackContext
from telegram.error import BadRequest


class ProgressValue(enum.Enum):
    LINES = '|', '/', '-', '\\'
    SPINNER = '◜', '◝', '◞', '◟'
    POINTS = '.', '..', '...'
    MOON_PHASES = '🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘'
    BLOCKS = '▒▒▒▒▒', '█▒▒▒▒', '██▒▒▒', '███▒▒', '████▒', '█████'
    RECTS_LARGE = '▢▢▢▢▢', '■▢▢▢▢', '■■▢▢▢', '■■■▢▢', '■■■■▢', '■■■■■'
    RECTS_SMALL = '□□□□□', '■□□□□', '■■□□□', '■■■□□', '■■■■□', '■■■■■'
    PARALLELOGRAMS = '▱', '▰▱▱▱▱', '▰▰▱▱▱', '▰▰▰▱▱', '▰▰▰▰▱', '▰▰▰▰▰'
    CIRCLES = '⚪⚪⚪⚪⚪', '⚫⚪⚪⚪⚪', '⚫⚫⚪⚪⚪', '⚫⚫⚫⚪⚪', '⚫⚫⚫⚫⚪', '⚫⚫⚫⚫⚫'

    @classmethod
    def get_text(
            cls,
            text_fmt: str = 'In progress {value} ({seconds} seconds)',
            value: str = '',
            seconds: int = 0,
    ) -> str:
        return text_fmt.format(value=value, seconds=seconds)

    def get_init_text(
            self,
            text_fmt: str = 'In progress {value} ({seconds} seconds)',
            seconds: int = 0,
    ) -> str:
        return self.get_text(
            value=self.value[0],
            seconds=seconds,
            text_fmt=text_fmt
        )


class InfinityProgressIndicatorThread(threading.Thread):
    def __init__(
            self,
            text_fmt: str,
            message: Message,
            progress_value: ProgressValue = ProgressValue.POINTS,
            parse_mode: ParseMode = None,
            reply_markup: ReplyMarkup = None,
            skip_progress: int = 1,
            init_seconds: int = 0,
            *args,
            **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.daemon = True

        self._stop = threading.Event()
        self._progress_bar = cycle(progress_value.value)

        for _ in range(skip_progress):
            next(self._progress_bar)

        self.text_fmt = text_fmt
        self.message = message
        self.parse_mode = parse_mode
        self.reply_markup = reply_markup

        self._seconds: int = init_seconds
        self.init_seconds: int = init_seconds

    def run(self):
        self._seconds = self.init_seconds

        while True:
            time.sleep(1)
            if self.is_stopped():
                break

            self._seconds += 1

            text = ProgressValue.get_text(
                text_fmt=self.text_fmt,
                value=next(self._progress_bar),
                seconds=self._seconds,
            )

            try:
                self.message.edit_text(
                    text=text,
                    parse_mode=self.parse_mode,
                    reply_markup=self.reply_markup,
                )
            except BadRequest:
                pass

    def stop(self):
        self._stop.set()

    def is_stopped(self) -> bool:
        return self._stop.is_set()


class show_temp_message:
    def __init__(
            self,
            text: str,
            update: Update,
            context: CallbackContext,
            parse_mode: ParseMode = None,
            reply_markup: ReplyMarkup = None,
            quote: bool = True,
            progress_value: ProgressValue = None,
            **kwargs,
    ):
        self.text = text
        self.update = update
        self.context = context
        self.parse_mode = parse_mode
        self.reply_markup = reply_markup
        self.quote = quote
        self.kwargs: dict = kwargs
        self.message: Message = None

        self.progress_value = progress_value
        self.thread_progress: InfinityProgressIndicatorThread = None

    def __enter__(self):
        text = self.text
        if self.progress_value:
            text = self.progress_value.get_init_text(self.text)

        self.message = self.update.effective_message.reply_text(
            text=text,
            parse_mode=self.parse_mode,
            reply_markup=self.reply_markup,
            quote=self.quote,
            **self.kwargs,
        )

        if self.progress_value:
            self.thread_progress = InfinityProgressIndicatorThread(
                text_fmt=self.text,
                message=self.message,
                progress_value=self.progress_value,
                parse_mode=self.parse_mode,
                reply_markup=self.reply_markup,
            )
            self.thread_progress.start()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.thread_progress:
            self.thread_progress.stop()

        if self.message:
            self.message.delete()


def show_temp_message_decorator(
        text: str = 'In progress...',
        parse_mode: ParseMode = None,
        reply_markup: ReplyMarkup = None,
        progress_value: ProgressValue = None,
        **kwargs,
):
    def actual_decorator(func):
        @functools.wraps(func)
        def wrapper(update: Update, context: CallbackContext):
            with show_temp_message(
                text=text,
                update=update,
                context=context,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                progress_value=progress_value,
                **kwargs,
            ):
                return func(update, context)

        return wrapper
    return actual_decorator
