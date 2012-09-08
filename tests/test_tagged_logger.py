# -*- coding: utf-8 -*-
import datetime
import pytz
import tagged_logger

def setup_function(func):
    tagged_logger.configure(host='localhost', port=6379, db=0,
                           prefix='test_tagged_logger')
    tagged_logger.full_cleanup()


def teardown_function(func):
    tagged_logger.full_cleanup()



def test_full_cleanup():
    assert tagged_logger.get() == []


def test_basic():
    tagged_logger.log('foo')
    tagged_logger.log('bar')
    records = tagged_logger.get()
    assert len(records) == 2
    # messages go in reverse time order
    assert str(records[0]) == 'bar'
    assert str(records[1]) == 'foo'


def test_objects():
    obj = {'foo': 'bar'}
    tagged_logger.log(obj)
    record = tagged_logger.get_latest()
    assert record.message == obj

def test_limit():
    tagged_logger.log('foo')
    tagged_logger.log('bar')
    records = tagged_logger.get(limit=1)
    assert len(records) == 1
    assert str(records[0]) == 'bar'


def test_tags():
    tagged_logger.log('random action')
    tagged_logger.log('foo created', tags=['foo',])
    tagged_logger.log('bar created', tags=['bar',])
    tagged_logger.log('foo gets bar', tags=['foo', 'bar'])
    all_records = tagged_logger.get()
    assert len(all_records) == 4
    foo_records = tagged_logger.get(tag='foo')
    assert len(foo_records) == 2


def test_implicit_timestamps():
    ts = datetime.datetime(2012, 1, 1, tzinfo=pytz.utc)
    tagged_logger.log('random action', ts=ts)
    record = tagged_logger.get_latest()
    assert record.ts == ts


def test_get_with_min_ts():
    ts = datetime.datetime(2012, 1, 1, tzinfo=pytz.utc)
    tagged_logger.log('1st January', ts=ts)
    tagged_logger.log('2nd January', ts=ts + datetime.timedelta(1))
    tagged_logger.log('3rd January', ts=ts + datetime.timedelta(2))

    min_ts = ts + datetime.timedelta(hours=1)
    records = tagged_logger.get(min_ts=min_ts)
    assert len(records) == 2
    assert str(records[0]) == '3rd January'
    assert str(records[1]) == '2nd January'


def test_get_with_max_ts():
    ts = datetime.datetime(2012, 1, 1, tzinfo=pytz.utc)
    tagged_logger.log('1st January', ts=ts)
    tagged_logger.log('2nd January', ts=ts + datetime.timedelta(1))
    tagged_logger.log('3rd January', ts=ts + datetime.timedelta(2))

    max_ts = ts + datetime.timedelta(2) - datetime.timedelta(hours=1)
    records = tagged_logger.get(max_ts=max_ts)
    assert len(records) == 2
    assert str(records[0]) == '2nd January'
    assert str(records[1]) == '1st January'



def test_get_with_min_and_max_ts():
    ts = datetime.datetime(2012, 1, 1, tzinfo=pytz.utc)
    tagged_logger.log('1st January', ts=ts)
    tagged_logger.log('2nd January', ts=ts + datetime.timedelta(1))
    tagged_logger.log('3rd January', ts=ts + datetime.timedelta(2))

    min_ts = ts + datetime.timedelta(hours=1)
    max_ts = ts + datetime.timedelta(2) - datetime.timedelta(hours=1)

    records = tagged_logger.get(min_ts=min_ts, max_ts=max_ts)
    assert len(records) == 1
    assert str(records[0]) == '2nd January'


def test_naive_ts():
    tagged_logger.log('foo')
    tagged_logger.log('bar')
    tagged_logger.log('baz')
    min_ts = datetime.datetime.utcnow() - datetime.timedelta(seconds=60)
    records = tagged_logger.get(min_ts=min_ts)
    assert len(records) == 3
