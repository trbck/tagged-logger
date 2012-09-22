# -*- coding: utf-8 -*-
import pytest
import pytz
import tagged_logger
import datetime
from .tools import setup_function, teardown_function


@pytest.mark.fresh
def test_expire():
    tagged_logger.log('1st January', expire=datetime.datetime(2012, 1, 1))
    tagged_logger.log('2nd January', expire=datetime.datetime(2012, 1, 2))

    expired = tagged_logger.expire(datetime.datetime(2011, 12, 30, 23, 59))
    assert expired == 0
    assert len(tagged_logger.get()) == 2  # nothing has expired

    expired = tagged_logger.expire(datetime.datetime(2012, 1, 1, 23, 59))
    assert expired == 1
    assert len(tagged_logger.get()) == 1  # one message has expired

    expired = tagged_logger.expire(datetime.datetime(2012, 1, 2, 23, 59))
    assert expired == 1
    assert len(tagged_logger.get()) == 0  # all messages have expired


def test_expire_timedelta():
    """
    expire parameter can be a timedelta
    """
    tagged_logger.log('+1 second',
                      ts=datetime.datetime(2012, 1, 1),
                      expire=datetime.timedelta(seconds=1))
    record = tagged_logger.get_latest()
    assert record.expire == pytz.utc.localize(datetime.datetime(2012, 1, 1, 0, 0, 1))


def test_expire_integer():
    """
    expire parameter can be an integer
    """
    tagged_logger.log('+1 second',
                      ts=datetime.datetime(2012, 1, 1),
                      expire=1)
    record = tagged_logger.get_latest()
    assert record.expire == pytz.utc.localize(datetime.datetime(2012, 1, 1, 0, 0, 1))
