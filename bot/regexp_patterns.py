#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import datetime as DT
import re

from bot.third_party.regexp import fill_string_pattern


COMMAND_ADMIN_STATS = 'admin_stats'
REPLY_ADMIN_STATS = 'Статистика админа'

COMMAND_LAST = 'Последнее значение'
PATTERN_INLINE_GET_BY_DATE = re.compile(r'^get_by_date=(.+)$')

PATTERN_REPLY_SELECT_DATE = re.compile(r'^Выбрать дату', flags=re.IGNORECASE)
PATTERN_INLINE_SELECT_DATE = re.compile(r'.+;\d+;\d+;\d+')  # NOTE: Формат telegramcalendar.py

PATTERN_INLINE_GET_CHART_CURRENCY_BY_YEAR = re.compile(r'^get_chart currency=(.+) year=(.+)$')

COMMAND_LAST_BY_WEEK = 'За неделю'
COMMAND_LAST_BY_MONTH = 'За месяц'
COMMAND_GET_ALL = 'За всё время'

COMMAND_SUBSCRIBE = 'Подписаться'
COMMAND_UNSUBSCRIBE = 'Отписаться'


if __name__ == '__main__':
    assert fill_string_pattern(PATTERN_INLINE_GET_BY_DATE, DT.date(2022, 4, 1)) == 'get_by_date=2022-04-01'

    assert fill_string_pattern(PATTERN_INLINE_GET_CHART_CURRENCY_BY_YEAR, 'USD', 2022) \
           == 'get_chart currency=USD year=2022'
    assert fill_string_pattern(PATTERN_INLINE_GET_CHART_CURRENCY_BY_YEAR, 'USD', -1) \
           == 'get_chart currency=USD year=-1'
