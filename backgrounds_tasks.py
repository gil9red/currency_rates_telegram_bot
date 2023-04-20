#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from threading import Thread

from bot.run_check_subscriptions import sending_notifications
from parser.main import run_parser


def run():
    Thread(target=run_parser).start()
    Thread(target=sending_notifications).start()
