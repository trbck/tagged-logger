#  -*- coding: utf-8 -*-
import tagged_logger

def setup_function(func):
    tagged_logger.configure(host='localhost', port=6379, db=0,
        prefix='test_tagged_logger')
    tagged_logger.full_cleanup()
    tagged_logger.reset_context()


def teardown_function(func):
    tagged_logger.full_cleanup()