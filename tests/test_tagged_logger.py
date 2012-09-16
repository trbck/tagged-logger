# -*- coding: utf-8 -*-
import time
import datetime
import pytz
import threading
import tagged_logger

from .tools import setup_function, teardown_function

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


def test_context_tags():
    with tagged_logger.context(tags=['foo', 'bar']):
        with tagged_logger.context(tags=['baz']):
            tagged_logger.log('Random message', tags=['spam', ])
    for tag in ('__all__', 'foo', 'bar', 'baz', 'spam'):
        assert len(tagged_logger.get(tag)) == 1


def test_context_attrs_dict():
    """
    dictionary log message can be extended with attributes
    """
    with tagged_logger.context(attrs={'remote_addr': '127.0.0.1'}):
        tagged_logger.log({'text': 'foo bar'})
    record = tagged_logger.get_latest()
    assert record.message['text'] == 'foo bar'
    assert record.message['remote_addr'] == '127.0.0.1'


def test_context_attrs_str():
    """
    text log message silently ignores extended attributes
    """
    with tagged_logger.context(attrs={'remote_addr': '127.0.0.1'}):
        tagged_logger.log('foo bar')
    record = tagged_logger.get_latest()
    assert record.message == 'foo bar'


def test_context_add_tags():
    """
    It is possible to manually add tags to context
    """
    tagged_logger.add_tags('foo', 'bar')
    tagged_logger.log('sample message')
    assert len(tagged_logger.get('foo')) == 1
    assert len(tagged_logger.get('bar')) == 1


def test_context_rm_tags():
    """
    You can remove tags also
    """
    tagged_logger.add_tags('foo', 'bar')
    tagged_logger.rm_tags('foo')
    tagged_logger.rm_tags('bar')
    tagged_logger.rm_tags('baz')
    tagged_logger.log('sample message')
    assert len(tagged_logger.get('foo')) == 0
    assert len(tagged_logger.get('bar')) == 0


def test_context_add_attrs():
    tagged_logger.add_attrs(remote_addr='127.0.0.1')
    tagged_logger.log({'text': 'sample message'})
    record = tagged_logger.get_latest()
    assert record.message['remote_addr'] == '127.0.0.1'


def test_context_rm_attrs():
    tagged_logger.add_attrs(remote_addr='127.0.0.1')
    tagged_logger.rm_attrs('remote_addr', 'baz')
    tagged_logger.log({'text': 'sample message'})
    record = tagged_logger.get_latest()
    assert record.message == {'text': 'sample message'}


def test_context_reset():
    tagged_logger.add_tags('foo', 'bar')
    tagged_logger.reset_context()
    tagged_logger.log('foo bar')
    assert len(tagged_logger.get('foo')) == 0
    assert len(tagged_logger.get('bar')) == 0


def _log_foo():
    with tagged_logger.context(tags=['foo']):
        tagged_logger.log('foo')
        time.sleep(0.2)

def _log_bar():
    with tagged_logger.context(tags=['bar']):
        tagged_logger.log('bar')
        time.sleep(0.2)


def test_context_multithread():
    foo_thread = threading.Thread(target=_log_foo)
    bar_thread = threading.Thread(target=_log_bar)
    foo_thread.start()
    time.sleep(0.1)
    bar_thread.start()
    foo_thread.join()
    bar_thread.join()

    # check results

    foo_records = tagged_logger.get('foo')
    assert len(foo_records) == 1
    assert str(foo_records[0]) == 'foo'

    bar_records = tagged_logger.get('bar')
    assert len(bar_records) == 1
    assert str(bar_records[0]) == 'bar'
