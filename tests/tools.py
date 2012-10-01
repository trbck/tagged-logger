#  -*- coding: utf-8 -*-
import tagged_logger

prefix = 'test_taged_logger'
redis_kwargs = dict(host='localhost', port=6379, db=0)

def setup_function(func):
    tagged_logger.configure(prefix, **redis_kwargs)
    tagged_logger.full_cleanup()
    tagged_logger.reset_context()


def teardown_function(func):
    tagged_logger.full_cleanup()
