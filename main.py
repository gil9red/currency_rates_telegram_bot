#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import os
import time
from threading import Thread

# pip install python-telegram-bot
from telegram.ext import Updater, Defaults

import db
from config import TOKEN, PATH_GRAPH_WEEK, PATH_GRAPH_MONTH
from graph import create_graph
from parser_exchange_rate import parse
from run_check_subscriptions import check

from bot import commands
from bot.common import log


def main():
    log.debug('Start')

    cpu_count = os.cpu_count()
    workers = cpu_count
    log.debug(f'System: CPU_COUNT={cpu_count}, WORKERS={workers}')

    updater = Updater(
        TOKEN,
        workers=workers,
        defaults=Defaults(run_async=True),
    )
    bot = updater.bot
    log.debug(f'Bot name {bot.first_name!r} ({bot.name})')

    Thread(target=check, args=[updater.bot]).start()

    dp = updater.dispatcher
    commands.setup(dp)

    updater.start_polling()
    updater.idle()

    log.debug('Finish')


def loop_parse_and_check_graph():
    while True:
        parse()

        items = db.ExchangeRate.get_last_by(days=7)
        create_graph(items, PATH_GRAPH_WEEK)

        items = db.ExchangeRate.get_last_by(days=30)
        create_graph(items, PATH_GRAPH_MONTH)

        time.sleep(8 * 3600)


if __name__ == '__main__':
    Thread(target=loop_parse_and_check_graph).start()

    while True:
        try:
            main()
        except:
            log.exception('')

            timeout = 15
            log.info(f'Restarting the bot after {timeout} seconds')
            time.sleep(timeout)
