# -*- coding: utf-8 -*-
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


def test_tags():
    tagged_logger.log('random action')
    tagged_logger.log('foo created', tags=['foo',])
    tagged_logger.log('bar created', tags=['bar',])
    tagged_logger.log('foo gets bar', tags=['foo', 'bar'])
    all_records = tagged_logger.get()
    assert len(all_records) == 4
    foo_records = tagged_logger.get(tag='foo')
    assert len(foo_records) == 2
