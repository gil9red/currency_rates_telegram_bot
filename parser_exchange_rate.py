#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import datetime as DT
from decimal import Decimal
from typing import Tuple

import requests
from bs4 import BeautifulSoup

import db
from bot.common import get_date_str


def get_last_currencies() -> tuple[DT.date, dict[str, Decimal]]:
    url = 'https://www.cbr.ru/scripts/XML_daily.asp'

    rs = requests.get(url)
    root = BeautifulSoup(rs.content, 'html.parser')

    date = DT.datetime.strptime(root.valcurs['date'], '%d.%m.%Y')
    currency_by_value = dict()

    for s in root.find_all('valute'):
        currency = s.charcode.string
        value = Decimal(s.value.string.replace(',', '.'))
        currency_by_value[currency] = value

    return date, currency_by_value


# TODO: удалить, использовать get_last_currencies
def get_last_usd() -> Tuple[DT.date, Decimal]:
    date, currency_by_value = get_last_currencies()
    value = currency_by_value.get('USD')
    if value:
        return date, value

    raise Exception('Не удалось найти значение USD!')


def parse():
    date, value = get_last_usd()

    exchange_rate = db.ExchangeRate.get_or_none(db.ExchangeRate.date == date)
    if not exchange_rate:
        db.ExchangeRate.create(date=date, value=value)
        print(f'Добавлено: {get_date_str(date)} = {value}')

        db.Subscription.update(was_sending=False).execute()


if __name__ == '__main__':
    date, currency_by_value = get_last_currencies()
    print(f'Дата {get_date_str(date)}. Валют ({len(currency_by_value)}): {currency_by_value}')

    parse()
