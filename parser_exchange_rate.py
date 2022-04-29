#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import datetime as DT
import time
from decimal import Decimal

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


# TODO: Добавить логгер
def parse():
    date, currency_by_value = get_last_currencies()

    old_count = db.ExchangeRate.count()
    for currency_code, value in currency_by_value.items():
        rate = db.ExchangeRate.get_by(date=date, currency_code=currency_code)
        if not rate:
            db.ExchangeRate.add(
                date=date,
                currency_code=currency_code,
                value=value,
            )
            print(f'За {get_date_str(date)} добавлено {currency_code} = {value}')

    diff_count = db.ExchangeRate.count() - old_count
    if diff_count > 0:
        print(f'Было добавлено {diff_count} записей')
        db.Subscription.update(was_sending=False).execute()


def run():
    while True:
        parse()
        time.sleep(8 * 60 * 60)  # 8 hours


if __name__ == '__main__':
    date, currency_by_value = get_last_currencies()
    print(f'Дата {get_date_str(date)}. Валют ({len(currency_by_value)}): {currency_by_value}')

    run()
