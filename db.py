#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import datetime as DT
import enum
import time
from decimal import Decimal
from typing import Type, List, Iterable, Optional

# pip install peewee
from peewee import (
    Field, DateField, DecimalField, BooleanField,
    Model, TextField, ForeignKeyField, CharField, IntegerField, DateTimeField
)
from playhouse.sqliteq import SqliteQueueDatabase

from config import DB_FILE_NAME
from bot.common import get_date_str, SubscriptionResultEnum


ITEMS_PER_PAGE: int = 10


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

    @classmethod
    def get_first(cls) -> Type['BaseModel']:
        return cls.select().first()

    @classmethod
    def get_last(cls) -> Type['BaseModel']:
        return cls.select().order_by(cls.id.desc()).first()

    @classmethod
    def paginating(
            cls,
            page: int = 1,
            items_per_page: int = ITEMS_PER_PAGE,
            order_by: Field = None,
            filters: Iterable = None,
    ) -> list[Type['BaseModel']]:
        query = cls.select()

        if filters:
            query = query.filter(*filters)

        if order_by:
            query = query.order_by(order_by)

        query = query.paginate(page, items_per_page)
        return list(query)

    @classmethod
    def get_inherited_models(cls) -> list[Type['BaseModel']]:
        return sorted(cls.__subclasses__(), key=lambda x: x.__name__)

    @classmethod
    def count(cls) -> int:
        return cls.select().count()

    @classmethod
    def print_count_of_tables(cls):
        items = []
        for sub_cls in cls.get_inherited_models():
            name = sub_cls.__name__
            count = sub_cls.count()
            items.append(f'{name}: {count}')

        print(', '.join(items))

    def __str__(self):
        fields = []
        for k, field in self._meta.fields.items():
            v = getattr(self, k)

            if isinstance(field, (TextField, CharField)):
                if v:
                    if isinstance(v, enum.Enum):
                        v = v.value

                    v = repr(shorten(v))

            elif isinstance(field, ForeignKeyField):
                k = f'{k}_id'
                if v:
                    v = v.id

            fields.append(f'{k}={v}')

        return self.__class__.__name__ + '(' + ', '.join(fields) + ')'


class ExchangeRate(BaseModel):
    date = DateField()
    currency_code = TextField()
    value = DecimalField(decimal_places=4, auto_round=True)

    class Meta:
        indexes = (
            (('date', 'currency_code'), True),
        )

    @classmethod
    def get_by(cls, date: DT.date, currency_code: str) -> Optional['ExchangeRate']:
        return cls.get_or_none(date=date, currency_code=currency_code)

    @classmethod
    def add(
            cls,
            date: DT.date,
            currency_code: str,
            value: Decimal,
    ) -> 'ExchangeRate':
        obj = cls.get_by(date=date, currency_code=currency_code)
        if not obj:
            obj = cls.create(
                date=date,
                currency_code=currency_code,
                value=value,
            )

        return obj

    @classmethod
    def get_last_dates(cls, number: int = -1) -> list[DT.date]:
        query = cls.select(cls.date).distinct().limit(number).order_by(cls.date.desc())
        return [rate.date for rate in query]

    @classmethod
    def get_last_date(cls) -> DT.date:
        return cls.get_last_dates(number=1)[0]

    @classmethod
    def get_last_by(cls, currency_code: str) -> Optional['ExchangeRate']:
        return cls.get_by(
            date=cls.get_last_date(),
            currency_code=currency_code,
        )

    @classmethod
    def get_last_rates(cls, currency_code: str, number: int = -1) -> List['ExchangeRate']:
        dates = cls.get_last_dates(number)
        query = cls.select().where(cls.currency_code == currency_code, cls.date.in_(dates)).order_by(cls.date.asc())
        return list(query)

    @classmethod
    def get_prev_next_dates(cls, date: DT.date, currency_code: str) -> tuple[DT.date, DT.date]:
        prev_val = (
            cls.select(cls.date)
                .where(cls.date < date, cls.currency_code == currency_code)
                .limit(1)
                .order_by(cls.date.desc())
                .first()
        )
        prev_date = prev_val.date if prev_val else None

        next_val = (
            cls.select(cls.date)
                .where(cls.date > date, cls.currency_code == currency_code)
                .limit(1)
                .order_by(cls.date.asc())
                .first()
        )
        next_date = next_val.date if next_val else None

        return prev_date, next_date

    def get_description(self, show_diff: bool = True) -> str:
        def get_diff_str(prev_amt: DecimalField, next_amt: DecimalField) -> str:
            diff = next_amt - prev_amt
            abs_diff = abs(diff)

            # Если разница целочисленная, то оставляем целым числом
            if abs_diff % 1 == 0:
                abs_diff = int(abs_diff)
            else:
                # Иначе вещественным, но с точностью в 2 знака
                abs_diff = f'{abs_diff:.4f}'

            sign = "-" if diff < 0 else "+"
            return f'{sign}{abs_diff}'

        prev_date, _ = self.get_prev_next_dates(date=self.date, currency_code=self.currency_code)
        text_diff_value = ''
        if prev_date and show_diff:
            prev_rate = self.get_by(date=prev_date, currency_code=self.currency_code)
            text_diff_value = f' ({get_diff_str(prev_rate.value, self.value)})'

        return f'{self.currency_code}: {self.value:.4f}{text_diff_value}'

    @classmethod
    def get_full_description(cls, currency_code_list: list[str], show_diff: bool = True) -> str:
        date = cls.get_last_date()

        lines = [
            f'Актуальный курс за <b><u>{get_date_str(date)}</u></b>:'
        ]
        for currency_code in currency_code_list:
            rate = cls.get_by(date, currency_code)
            lines.append(f'    {rate.get_description(show_diff)}')

        return '\n'.join(lines)


class Subscription(BaseModel):
    user_id = IntegerField(unique=True)
    is_active = BooleanField(default=True)
    was_sending = BooleanField(default=True)
    creation_datetime = DateTimeField(default=DT.datetime.now)
    modification_datetime = DateTimeField(default=DT.datetime.now)

    @classmethod
    def get_by_user_id(cls, user_id: int) -> Optional['Subscription']:
        return cls.get_or_none(cls.user_id == user_id)

    @classmethod
    def subscribe(cls, user_id: int) -> SubscriptionResultEnum:
        # Если подписка уже есть
        if cls.has_is_active(user_id):
            return SubscriptionResultEnum.ALREADY

        obj = cls.get_by_user_id(user_id)
        if obj:
            obj.set_active(True)
        else:
            # По-умолчанию, подписки создаются активными
            cls.create(user_id=user_id)

        return SubscriptionResultEnum.SUBSCRIBE_OK

    @classmethod
    def unsubscribe(cls, user_id: int) -> SubscriptionResultEnum:
        # Если подписка и так нет
        if not cls.has_is_active(user_id):
            return SubscriptionResultEnum.ALREADY

        obj = cls.get_by_user_id(user_id)
        if obj:
            obj.set_active(False)

        return SubscriptionResultEnum.UNSUBSCRIBE_OK

    @classmethod
    def get_active_unsent_subscriptions(cls) -> list['Subscription']:
        return cls.select().where(cls.was_sending == False, cls.is_active == True)

    @classmethod
    def has_is_active(cls, user_id: int) -> bool:
        return bool(cls.get_or_none(cls.user_id == user_id, cls.is_active == True))

    def set_active(self, active: bool):
        self.is_active = active
        if active:  # Чтобы сразу после подписки бот не отправил рассылку
            self.was_sending = True
        self.modification_datetime = DT.datetime.now()
        self.save()


db.connect()
db.create_tables(BaseModel.get_inherited_models())

# Задержка в 50мс, чтобы дать время на запуск SqliteQueueDatabase и создание таблиц
# Т.к. в SqliteQueueDatabase запросы на чтение выполняются сразу, а на запись попадают в очередь
time.sleep(0.050)


if __name__ == '__main__':
    BaseModel.print_count_of_tables()

    print()

    print(get_date_str(ExchangeRate.get_last().date))
    print()

    print('\n' + '-' * 10 + '\n')

    rate = ExchangeRate.get_last_by('USD')
    print(rate)
    print(rate.get_description())

    print('\n' + '-' * 10 + '\n')

    for rate in ExchangeRate.get_last_rates('USD', number=3):
        print(rate)
        print(rate.get_description())
        print()
