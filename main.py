#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import os
import time
from threading import Thread

# pip install python-telegram-bot
from telegram.ext import Updater, Defaults

from root_config import TOKEN

from bot import commands
from bot.common import log
from bot.run_check_subscriptions import sending_notifications
from parser.main import run as run_parser


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

    dp = updater.dispatcher
    commands.setup(dp)

    updater.start_polling()
    updater.idle()

    log.debug('Finish')


if __name__ == '__main__':
    Thread(target=run_parser).start()
    Thread(target=sending_notifications, args=[log]).start()

    while True:
        try:
            main()
        except:
            log.exception('')

            timeout = 15
            log.info(f'Restarting the bot after {timeout} seconds')
            time.sleep(timeout)
