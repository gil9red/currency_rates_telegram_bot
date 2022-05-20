#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import datetime as DT
import re

from bot.third_party.regexp import fill_string_pattern


COMMAND_ADMIN_STATS = 'admin_stats'
PATTERN_REPLY_ADMIN_STATS = re.compile(r'^Статистика админа$|^Admin stats$', flags=re.IGNORECASE)

COMMAND_SETTINGS = 'settings'
PATTERN_REPLY_SETTINGS = re.compile(r'^Настройки$|^Settings$', flags=re.IGNORECASE)

PATTERN_REPLY_COMMAND_LAST = re.compile(r'^Последнее значение$', flags=re.IGNORECASE)
REPLY_COMMAND_LAST = fill_string_pattern(PATTERN_REPLY_COMMAND_LAST)
PATTERN_INLINE_GET_BY_DATE = re.compile(r'^get_by_date=(.+)$')

PATTERN_REPLY_SELECT_DATE = re.compile(r'^Выбрать дату$', flags=re.IGNORECASE)
PATTERN_INLINE_SELECT_DATE = re.compile(r'.+;\d+;\d+;\d+')  # NOTE: Формат telegramcalendar.py

PATTERN_INLINE_GET_CHART_CURRENCY_BY_YEAR = re.compile(r'^get_chart currency=(.+) year=(.+)$')

PATTERN_INLINE_SETTINGS_SELECT_CURRENCY_CHAR_CODE = re.compile(r'^settings_select_currency_char_code=(.+)$')

PATTERN_REPLY_SHOW_ALL_CURRENCIES = re.compile(r'^Все валюты$', flags=re.IGNORECASE)
PATTERN_INLINE_SHOW_ALL_CURRENCIES = re.compile(r'^show_all_currencies$')

CALLBACK_IGNORE = 'IGNORE'

PATTERN_REPLY_COMMAND_LAST_BY_WEEK = re.compile(r'^За неделю$', flags=re.IGNORECASE)
PATTERN_REPLY_COMMAND_LAST_BY_MONTH = re.compile(r'^За месяц$', flags=re.IGNORECASE)
PATTERN_REPLY_COMMAND_GET_ALL = re.compile(r'^За вс[её] время$', flags=re.IGNORECASE)
PATTERN_INLINE_GET_CHART_CURRENCY_BY_NUMBER = re.compile(r'^get_chart currency=(.+) number=(.+)$')

PATTERN_REPLY_COMMAND_SUBSCRIBE = re.compile(r'^Подписаться$', flags=re.IGNORECASE)
PATTERN_REPLY_COMMAND_UNSUBSCRIBE = re.compile(r'^Отписаться$', flags=re.IGNORECASE)


if __name__ == '__main__':
    assert fill_string_pattern(PATTERN_INLINE_GET_BY_DATE, DT.date(2022, 4, 1)) == 'get_by_date=2022-04-01'

    assert fill_string_pattern(PATTERN_INLINE_GET_CHART_CURRENCY_BY_YEAR, 'USD', 2022) \
           == 'get_chart currency=USD year=2022'
    assert fill_string_pattern(PATTERN_INLINE_GET_CHART_CURRENCY_BY_YEAR, 'USD', -1) \
           == 'get_chart currency=USD year=-1'

    assert REPLY_COMMAND_LAST == 'Последнее значение'
