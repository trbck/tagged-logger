# -*- coding: utf-8 -*-
import time
import multiprocessing
import tagged_logger
from .tools import setup_function, teardown_function

def do_generate_two_records():
    time.sleep(0.2)
    tagged_logger.log('foo')
    tagged_logger.log('bar')


def test_pubsub():
    generator = multiprocessing.Process(target=do_generate_two_records)
    generator.start()
    messages = []
    tagged_logger.subscribe()
    for message in tagged_logger.listen():
        messages.append(message)
        if len(messages) == 2:
            break
    tagged_logger.unsubscribe()
    generator.join()
    msg1, msg2 = messages
    assert isinstance(msg1, tagged_logger.Log)
    assert isinstance(msg2, tagged_logger.Log)
    assert msg1.message == 'foo'
    assert msg2.message == 'bar'