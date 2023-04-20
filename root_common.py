#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import datetime as DT
import inspect
import logging
import sys

from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Union

from root_config import DATE_FORMAT


def get_start_date(year: int) -> DT.date:
    return DT.date(year, 1, 1)


def get_end_date(year: int) -> DT.date:
    return DT.date(year + 1, 1, 1) - DT.timedelta(days=1)


def get_date_str(date: DT.date) -> str:
    return date.strftime(DATE_FORMAT)


def caller_name() -> str:
    """Return the calling function's name."""
    return inspect.currentframe().f_back.f_code.co_name


# SOURCE: https://github.com/gil9red/telegram__random_bashim_bot/blob/4042e9664eea997271eaca2c8ad523b0afdf63fb/common.py#L52
def split_list(items: list, columns: int = 5) -> list[list]:
    result = []

    for i in range(0, len(items), columns):
        result.append(
            [key for key in items[i: i + columns]]
        )

    return result


def get_logger(
    name: str,
    file: Union[str, Path] = "log.txt",
    encoding="utf-8",
    log_stdout=True,
    log_file=True,
) -> "logging.Logger":
    log = logging.getLogger(name)

    # Возвращаем уже существующий логгер
    if log.handlers:
        return log

    log.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "[%(asctime)s] %(filename)s:%(lineno)d %(levelname)-8s %(message)s"
    )

    if log_file:
        fh = RotatingFileHandler(
            file, maxBytes=10000000, backupCount=5, encoding=encoding
        )
        fh.setFormatter(formatter)
        log.addHandler(fh)

    if log_stdout:
        sh = logging.StreamHandler(stream=sys.stdout)
        sh.setFormatter(formatter)
        log.addHandler(sh)

    return log
