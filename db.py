#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import datetime as DT
import time
from typing import Type, List

# pip install peewee
from peewee import (
    DateField, DecimalField, BooleanField,
    Model, TextField, ForeignKeyField, CharField, IntegerField, DateTimeField
)
from playhouse.sqliteq import SqliteQueueDatabase

from config import DB_FILE_NAME
from bot.common import get_date_str


def shorten(text: str, length=30) -> str:
    if not text:
        return text

    if len(text) > length:
        text = text[:length] + '...'
    return text


# This working with multithreading
# SOURCE: http://docs.peewee-orm.com/en/latest/peewee/playhouse.html#sqliteq
db = SqliteQueueDatabase(
    DB_FILE_NAME,
    pragmas={
        'foreign_keys': 1,
        'journal_mode': 'wal',  # WAL-mode
        'cache_size': -1024 * 64  # 64MB page-cache
    },
    use_gevent=False,  # Use the standard library "threading" module.
    autostart=True,
    queue_max_size=64,  # Max. # of pending writes that can accumulate.
    results_timeout=5.0  # Max. time to wait for query to be executed.
)


class BaseModel(Model):
    """
    Базовая модель для классов-таблиц
    """

    class Meta:
        database = db

    def get_new(self) -> Type['BaseModel']:
        return type(self).get(self._pk_expr())

    def __str__(self):
        fields = []
        for k, field in self._meta.fields.items():
            v = getattr(self, k)

            if isinstance(field, (TextField, CharField)):
                if v:
                    v = repr(shorten(v))

            elif isinstance(field, ForeignKeyField):
                k = f'{k}_id'
                if v:
                    v = v.id

            fields.append(f'{k}={v}')

        return self.__class__.__name__ + '(' + ', '.join(fields) + ')'


class ExchangeRate(BaseModel):
    date = DateField(unique=True)
    value = DecimalField()

    @classmethod
    def get_last(cls) -> 'ExchangeRate':
        return cls.select().order_by(cls.id.desc()).first()

    @classmethod
    def get_last_by(cls, days: int) -> List['ExchangeRate']:
        date = DT.datetime.now() - DT.timedelta(days=days)
        return list(cls.select().where(cls.date >= date))


class Subscription(BaseModel):
    chat_id = IntegerField(unique=True)
    is_active = BooleanField(default=True)
    was_sending = BooleanField(default=False)
    creation_datetime = DateTimeField(default=DT.datetime.now)
    modification_datetime = DateTimeField(default=DT.datetime.now)

    @classmethod
    def get_active_unsent_subscriptions(cls) -> List['Subscription']:
        return cls.select().where(cls.was_sending == False, cls.is_active == True)

    @classmethod
    def get_is_active(cls, chat_id) -> 'Subscription':
        return cls.get_or_none(cls.chat_id == chat_id, cls.is_active)

    def set_active(self, active: bool):
        self.is_active = active
        if not active:
            self.was_sending = False
        self.modification_datetime = DT.datetime.now()
        self.save()


db.connect()

db.create_tables([ExchangeRate, Subscription])

# Задержка в 50мс, чтобы дать время на запуск SqliteQueueDatabase и создание таблиц
# Т.к. в SqliteQueueDatabase запросы на чтение выполняются сразу, а на запись попадают в очередь
time.sleep(0.050)


if __name__ == '__main__':
    print(ExchangeRate.select().count())
    print(ExchangeRate.get(ExchangeRate.id == 1).value)

    # Subscription.truncate_table()
    for s in Subscription.select():
        print(s.id, s.chat_id, s.was_sending)
    for s in ExchangeRate.select():
        print(s.date, s.value)

    print(Subscription.select().where(Subscription.is_active == True).count())

    print(get_date_str(ExchangeRate.select().first().date))
    print(get_date_str(ExchangeRate.get_last().date))

    print(Subscription.get_is_active(973083137))
