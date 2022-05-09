#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import time

from telegram import Bot, ParseMode

import db
from root_common import caller_name, get_logger
from root_config import DIR_LOGS, TOKEN, DEFAULT_CURRENCY_CODES  # TODO: Использовать настройки юзера


log = get_logger(__file__, DIR_LOGS / 'notifications.txt')


def sending_notifications():
    prefix = f'[{caller_name()}]'

    bot = Bot(TOKEN)

    log.info(f'{prefix} Запуск')
    log.debug(f'{prefix} Имя бота {bot.first_name!r} ({bot.name})')

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

    log.info(f'{prefix} Завершение')
