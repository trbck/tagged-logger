# -*- coding: utf-8 -*-
import tagged_logger
from tagged_logger import ta
from .tools import setup_function, teardown_function


def test_log_and_get():
    tagged_logger.log('{user} is from {ip}', ta(user='foo', ip='127.0.0.1'))
    tagged_logger.log('random message')
    record = tagged_logger.get_latest(user='foo')
    assert set(record.tags) == set(['user:foo', 'ip:127.0.0.1'])
    assert record.attrs == {'user': 'foo', 'ip': '127.0.0.1'}


def test_log_and_get_ta():
    tagged_logger.log('{user} is from {ip}', ta(user='foo', ip='127.0.0.1'))
    tagged_logger.log('random message')
    record = tagged_logger.get_latest(ta(user='foo'))
    assert set(record.tags) == set(['user:foo', 'ip:127.0.0.1'])
    assert record.attrs == {'user': 'foo', 'ip': '127.0.0.1'}

def test_context():
    with tagged_logger.context(ta(user='foo', ip='127.0.0.1')):
        tagged_logger.log('{user} is from {ip}')
    tagged_logger.log('random message')
    record = tagged_logger.get_latest(user='foo')
    assert set(record.tags) == set(['user:foo', 'ip:127.0.0.1'])
    assert record.attrs == {'user': 'foo', 'ip': '127.0.0.1'}

def test_manual_injection():
    tagged_logger.add_tagging_attrs(ta(user='foo'), ip='127.0.0.1')
    tagged_logger.log('{user} is from {ip}')
    tagged_logger.rm_tagging_attrs(ta(user='foo'), ip='127.0.0.1')
    tagged_logger.log('random message')
    record = tagged_logger.get_latest(user='foo')
    assert set(record.tags) == set(['user:foo', 'ip:127.0.0.1'])
    assert record.attrs == {'user': 'foo', 'ip': '127.0.0.1'}
