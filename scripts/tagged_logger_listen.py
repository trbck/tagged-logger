#!/usr/bin/env python
# -*- coding: utf-8 -*-
import tagged_logger as logger
import argparse

options = None

def parse_args():
    global options
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--prefix')
    parser.add_argument('-T', '--time-format', default='[%F %T]')
    options = parser.parse_args()

def do_listen():
    logger.configure(prefix=options.prefix)
    logger.subscribe()
    for record in logger.listen():
        ts = record.ts.strftime(options.time_format)
        formatted = '{0} {1}'.format(ts, str(record))
        print(formatted)

if __name__ == '__main__':
    parse_args()
    try:
        do_listen()
    except KeyboardInterrupt:
        logger.unsubscribe()
    print("")
