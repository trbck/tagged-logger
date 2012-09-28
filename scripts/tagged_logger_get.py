#!/usr/bin/env python
# -*- coding: utf-8 -*-
import tagged_logger as logger
import argparse
from dateutil import parser

options = None

def parse_args():
    global options
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--prefix')
    parser.add_argument('-t', '--tag', default='__all__')
    parser.add_argument('-l', '--limit')
    parser.add_argument('--min-ts')
    parser.add_argument('--max-ts')
    parser.add_argument('-T', '--time-format', default='[%F %T]')
    options = parser.parse_args()

def do_get():
    logger.configure(prefix=options.prefix)
    min_ts = options.min_ts and parser.parse(options.min_ts)
    max_ts = options.max_ts and parser.parse(options.max_ts)
    records = logger.get(tag=options.tag, limit=options.limit,
                         min_ts=min_ts, max_ts=max_ts)
    for record in records:
        ts = record.ts.strftime(options.time_format)
        formatted = '{0} {1}'.format(ts, str(record))
        print(formatted)

if __name__ == '__main__':
    parse_args()
    do_get()
