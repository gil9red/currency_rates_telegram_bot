#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import os
import sys

from pathlib import Path


# Текущая папка, где находится скрипт
DIR = Path(__file__).resolve().parent

DIR_LOGS: Path = DIR / 'logs'
DIR_LOGS.mkdir(parents=True, exist_ok=True)

# Создание папки для базы данных
DB_DIR_NAME = DIR / 'database'
DB_DIR_NAME.mkdir(parents=True, exist_ok=True)

# Путь к файлу базы данных
DB_FILE_NAME = str(DB_DIR_NAME / 'database.sqlite')

TOKEN_FILE_NAME = DIR / 'TOKEN.txt'

try:
    TOKEN = os.environ.get('TOKEN') or TOKEN_FILE_NAME.read_text('utf-8').strip()
    if not TOKEN:
        raise Exception('TOKEN пустой!')

except:
    print(f'Нужно в {TOKEN_FILE_NAME.name} или в переменную окружения TOKEN добавить токен бота')
    TOKEN_FILE_NAME.touch()
    sys.exit()

USER_NAME_ADMINS = [
    '@ilya_petrash',
]

# TODO: Удалить и генерировать в памяти, без сохранения на диск
PATH_GRAPH_WEEK = 'img/graph_week.png'
PATH_GRAPH_MONTH = 'img/graph_month.png'

ERROR_TEXT = 'Возникла какая-то проблема. Попробуйте повторить запрос или попробовать чуть позже...'

MAX_MESSAGE_LENGTH = 4096

DATE_FORMAT: str = '%d/%m/%Y'
