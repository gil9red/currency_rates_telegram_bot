#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import datetime as DT
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Union

# pip install matplotlib
import matplotlib.dates as mdates
from matplotlib.figure import Figure

import db
from root_config import DATE_FORMAT
from root_common import get_date_str


# SOURCE: https://github.com/gil9red/get_metal_rates/blob/480a9866194578b732bf6c64666784a031e98035/utils/draw_plot.py#L23
def draw_plot(
        out: Union[str, Path, BinaryIO],
        days: list[DT.date],
        values: list[Decimal],
        locator: mdates.DateLocator = None,
        title: str = None,
        color: str = 'orange',
        date_format: str = DATE_FORMAT,
        axis_off: bool = False,
):
    if not locator:
        locator = mdates.AutoDateLocator()

    fig = Figure()
    ax = fig.subplots()
    ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
    ax.xaxis.set_major_locator(locator)

    lines = ax.plot(days, values)[0]
    lines.set_color(color)

    if title:
        ax.set_xlabel(title)

    fig.autofmt_xdate()

    if axis_off:
        ax.set_xticks([])
        ax.set_yticks([])

    fig.savefig(out, format='png')

    # После записи в файловый объект нужно внутренний указатель переместить в начало, иначе read не будет работать
    if hasattr(out, 'seek'):  # Для BinaryIO и ему подобных
        out.seek(0)


def get_plot_for_currency(
    currency_code: str,
    number: int = -1,
    year: int = None,
    title_format: str = "Стоимость {currency_code} в рублях за {start_date} - {end_date}",
) -> BytesIO:
    if year:
        rates = db.ExchangeRate.get_all_by_year(currency_code=currency_code, year=year)
    else:
        rates = db.ExchangeRate.get_last_rates(currency_code=currency_code, number=number)

    days = []
    values = []
    for rate in rates:
        days.append(rate.date)
        values.append(rate.value)

    title = title_format.format(
        currency_code=currency_code,
        start_date=get_date_str(days[0]),
        end_date=get_date_str(days[-1])
    )

    bytes_io = BytesIO()
    draw_plot(
        out=bytes_io,
        days=days,
        values=values,
        title=title,
    )
    return bytes_io


if __name__ == '__main__':
    current_dir = Path(__file__).resolve().parent
    images_dir = current_dir / 'chart_images'
    images_dir.mkdir(parents=True, exist_ok=True)

    currency_code = 'USD'

    number = -1
    path = images_dir / f'graph_{currency_code}_={number}.png'
    photo = get_plot_for_currency(currency_code=currency_code, number=number)
    path.write_bytes(photo.read())

    number = 30
    path = images_dir / f'graph_{currency_code}_={number}.png'
    photo = get_plot_for_currency(currency_code=currency_code, number=number)
    path.write_bytes(photo.read())

    number = 7
    path = images_dir / f'graph_{currency_code}_={number}.png'
    photo = get_plot_for_currency(currency_code=currency_code, number=number)
    path.write_bytes(photo.read())

    year = 2021
    path = images_dir / f'graph_{currency_code}_year{year}.png'
    photo = get_plot_for_currency(currency_code=currency_code, year=year)
    path.write_bytes(photo.read())

    year = 2022
    path = images_dir / f'graph_{currency_code}_year{year}.png'
    photo = get_plot_for_currency(currency_code=currency_code, year=year)
    path.write_bytes(photo.read())
