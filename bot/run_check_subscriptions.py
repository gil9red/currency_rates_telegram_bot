#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import logging
import time

from telegram import Bot, ParseMode

import db
from bot.common import caller_name
from root_config import DEFAULT_CURRENCY_CODES  # TODO: Использовать настройки юзера


def sending_notifications(bot: Bot, log: logging.Logger):
    prefix = f'[{caller_name()}]'

    while True:
        try:
            subscriptions = db.Subscription.get_active_unsent_subscriptions()
            if not subscriptions:
                continue

            text = f'<b>Рассылка</b>\n{db.ExchangeRate.get_full_description(DEFAULT_CURRENCY_CODES)}'
            for subscription in subscriptions:
                bot.send_message(
                    chat_id=subscription.user_id,  # Для приватных чатов chat_id равен user_id
                    text=text,
                    parse_mode=ParseMode.HTML,
                )

                subscription.was_sending = True
                subscription.save()

                time.sleep(0.4)

        except Exception:
            log.exception(f'{prefix} Ошибка:')
            time.sleep(60)

        finally:
            time.sleep(1)
