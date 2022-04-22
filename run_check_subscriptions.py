#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import time

from telegram import Bot, ParseMode

import db
from bot.common import get_date_str


def check(bot: Bot):
    while True:
        for s in db.Subscription.get_active_unsent_subscriptions():
            rate = db.ExchangeRate.get_last()

            bot.send_message(
                s.chat_id,
                f'Актуальный курс USD за <b><u>{get_date_str(rate.date)}</u></b>: {rate.value}₽',
                parse_mode=ParseMode.HTML
             )

            s.was_sending = True
            s.save()

        time.sleep(2)
