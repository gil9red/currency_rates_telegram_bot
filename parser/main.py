#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import datetime as DT
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterator

import requests
from bs4 import BeautifulSoup, Tag

import db
from root_common import get_date_str, caller_name, get_logger
from root_config import DIR_LOGS


log = get_logger(__file__, DIR_LOGS / 'parser.txt')


@dataclass
class Currency:
    num_code: int
    char_code: str
    name: str
    nominal: int
    value: Decimal
    raw_value: Decimal

    @classmethod
    def parse_from(cls, el: Tag) -> 'Currency':
        nominal = int(el.select_one('nominal').string)
        value = Decimal(el.select_one('value').string.replace(',', '.'))
        raw_value = value / nominal

        return cls(
            num_code=int(el.select_one('numcode').string),
            char_code=el.select_one('charcode').string,
            name=el.select_one('name').string,
            nominal=nominal,
            value=value,
            raw_value=raw_value,
        )


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


def get_currencies(date: DT.date) -> tuple[DT.date, dict[str, Currency]]:
    date_fmt = '%d.%m.%Y'
    date_req = date.strftime(date_fmt)

    url = 'https://www.cbr.ru/scripts/XML_daily.asp'

    rs = requests.get(url, params=dict(date_req=date_req))
    root = BeautifulSoup(rs.content, 'html.parser')

    currency_by_value = dict()
    date = DT.datetime.strptime(root.valcurs['date'], date_fmt).date()

    for s in root.find_all('valute'):
        currency = Currency.parse_from(s)
        currency_by_value[currency.char_code] = currency

    return date, currency_by_value


def parse(date_req: DT.date, prefix: str = '[parse]'):
    date, currency_by_value = get_currencies(date_req)
    log.debug(f'{prefix} Получена дата {date}, валют {len(currency_by_value)}')

    # Не за все даты на сайте есть информация
    if date != date_req:
        return

    old_count = db.ExchangeRate.count()
    for currency_char_code, currency in currency_by_value.items():
        number_code = currency.num_code
        if not db.Currency.get_by(number_code=number_code):
            db.Currency.add(
                number_code=number_code,
                char_code=currency.char_code,
                title=currency.name,
            )
            log.info(f'{prefix} Добавлена валюта: {currency}')

        rate = db.ExchangeRate.get_by(date=date, currency_char_code=currency_char_code)
        if not rate:
            value = currency.raw_value
            db.ExchangeRate.add(
                date=date,
                currency_char_code=currency_char_code,
                value=value,
            )
            log.info(f'{prefix} За {get_date_str(date)} добавлено {currency_char_code} = {value}')

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
            log.debug(f'{prefix} Проверка для {date_req}')

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
