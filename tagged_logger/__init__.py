# -*- coding: utf-8 -*-
import json
import datetime
import pytz
import redis
from functools import wraps
import time


_logger = None


def check_logger(func):
    """
    Decorator which checks whether a global logger is configured

    Used mostly internally
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not _logger:
            raise RuntimeError('Redis logger is not configured')
        return func(*args, **kwargs)
    return wrapper


def configure(prefix=None, **kwargs):
    """
    Configure logger

    :param prefix: prefix to store keys in redis database
    :param \*\*kwargs: arguments to be passed to Redis constructor
                       (`host`, `port` and `db` make sense)
    """
    global _logger
    if _logger:
        _logger.configure(prefix=prefix, **kwargs)
    else:
        _logger = Logger(prefix=prefix, **kwargs)
    return _logger


@check_logger
def full_cleanup():
    """
    Remove all records from the store
    """
    return _logger.full_cleanup()


@check_logger
def get(tag='__all__'):
    """
    Get all records from the store

    Log records are returned in the reverse time order (latest first)

    :param tag: if not equal to "__all__", then remove only records marked with
                the corresponding tag
    """
    return _logger.get(tag=tag)


@check_logger
def get_latest(tag='__all__'):
    """
    Get latest log record with a given tag or None
    """
    return _logger.get_latest(tag=tag)


def log(message, tags=None):
    """
    Create a new log record, optionally marked with one or more tags

    :type message: string or any jsonable object
    :type tags: list of strings
    """
    return _logger.log(message, tags=tags)


class Logger(object):

    def __init__(self, prefix=None, **kwargs):
        self.configure(prefix=prefix, **kwargs)

    def configure(self, prefix=None, **kwargs):
        self.prefix = prefix or ''
        self.redis = redis.Redis(**kwargs)

    def full_cleanup(self):
        templates = ['msg:*', 'flow:*', 'counter']
        for tmpl in templates:
            keys = self.redis.keys(self._key(tmpl))
            if keys:
                self.redis.delete(*keys)


    def log(self, message, tags=None):
        _id = self._id()
        timestamp = time.time()
        # save log record
        log_record_key = self._key('msg:{0}', _id)
        log_record_value = {
            'id': _id,
            'ts': timestamp,
            'message': message,
        }
        str_log_record = json.dumps(log_record_value)
        self.redis.set(log_record_key, str_log_record)
        # save log record reference to flows
        flow_all = self._key('flow:__all__')
        self.redis.lpush(flow_all, _id)
        for tag in tags or []:
            flow_key = self._key('flow:{0}', tag)
            self.redis.lpush(flow_key, _id)

    def get(self, tag='__all__'):
        key = self._key('flow:{0}', tag)
        record_ids = self.redis.lrange(key, 0, -1)
        if not record_ids:
            return []
        record_keys = [self._key('msg:{0}', _id) for _id in record_ids]
        records = self.redis.mget(record_keys)
        return [Log(record) for record in records]

    def get_latest(self, tag='__all__'):
        key = self._key('flow:{0}', tag)
        _ids = self.redis.lrange(key, 0, 1)
        if not _ids:
            return None
        msg_key = self._key('msg:{0}', _ids[0])
        record = self.redis.get(msg_key)
        return Log(record)


    def _id(self):
        cnt = self._key('counter')
        return self.redis.incr(cnt)


    def _key(self, key, *args, **kwargs):
        if self.prefix:
            template = '{0}:{1}'.format(self.prefix, key)
        else:
            template = key
        if args or kwargs:
            template = template.format(*args, **kwargs)
        return template


class Log(object):

    def __init__(self, record_str):
        record = json.loads(record_str)
        self.id = record['id']
        self.message = record['message']
        self.ts = datetime.datetime.fromtimestamp(record['ts'], pytz.utc)
        self.record = record

    def __str__(self):
        return str(self.message)

    def __unicode__(self):
        return unicode(self.message)

    def __repr__(self):
        return '<Log@%s: %r>' % (self.ts, self.message)
