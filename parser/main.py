#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import datetime as DT
import time
from decimal import Decimal
from typing import Iterator

import requests
from bs4 import BeautifulSoup

import db
from root_common import get_date_str, caller_name, get_logger
from root_config import DIR_LOGS


log = get_logger(__file__, DIR_LOGS / 'parser.txt')


def get_next_date(date: DT.date) -> DT.date:
    return date + DT.timedelta(days=1)


def iter_dates(start_date: DT.date, end_date: DT.date = None) -> Iterator[DT.date]:
    if not end_date:
        end_date = DT.date.today()

    date_req1 = start_date
    yield date_req1

    while True:
        date_req2 = get_next_date(date_req1)
        if date_req2 > end_date:
            break

        yield date_req2
        date_req1 = date_req2


def get_currencies(date: DT.date) -> tuple[DT.date, dict[str, Decimal]]:
    date_fmt = '%d.%m.%Y'
    date_req = date.strftime(date_fmt)

    url = 'https://www.cbr.ru/scripts/XML_daily.asp'

    rs = requests.get(url, params=dict(date_req=date_req))
    root = BeautifulSoup(rs.content, 'html.parser')

    currency_by_value = dict()
    date = DT.datetime.strptime(root.valcurs['date'], date_fmt).date()

    for s in root.find_all('valute'):
        currency = s.charcode.string
        value = Decimal(s.value.string.replace(',', '.')) / Decimal(s.nominal.string)
        currency_by_value[currency] = value

    return date, currency_by_value


def parse(date_req: DT.date, prefix: str = '[parse]'):
    date, currency_by_value = get_currencies(date_req)

    # Не за все даты на сайте есть информация
    if date != date_req:
        return

    old_count = db.ExchangeRate.count()
    for currency_code, value in currency_by_value.items():
        rate = db.ExchangeRate.get_by(date=date, currency_code=currency_code)
        if not rate:
            db.ExchangeRate.add(
                date=date,
                currency_code=currency_code,
                value=value,
            )
            log.info(f'{prefix} За {get_date_str(date)} добавлено {currency_code} = {value}')

    diff_count = db.ExchangeRate.count() - old_count
    if diff_count > 0:
        log.info(f'{prefix} Добавлено {diff_count} записей\n')

        db.Subscription.update(was_sending=False).execute()


def run_parser():
    prefix = f'[{caller_name()}]'

    log.info(f'{prefix} Запуск')

    while True:
        start_date = db.ExchangeRate.get_last_date()
        if db.ExchangeRate.count():  # Для существующих записей проверка идет для следующей даты
            start_date = get_next_date(start_date)

        i = 0
        for date_req in iter_dates(start_date):
            while True:
                try:
                    parse(date_req, prefix=prefix)

                except Exception:
                    log.exception(f'{prefix} Ошибка:')
                    time.sleep(3600 * 4)  # Wait 4 hours
                    continue

                break

            if i > 0:
                time.sleep(5)

            i += 1

        time.sleep(60 * 60)  # Every 1 hour

    log.info(f'{prefix} Завершение')


if __name__ == '__main__':
    date, currency_by_value = get_currencies(DT.date.today())
    print(f'Дата {get_date_str(date)}. Валют ({len(currency_by_value)}): {currency_by_value}')

    run_parser()
