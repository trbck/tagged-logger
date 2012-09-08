# -*- coding: utf-8 -*-
import calendar
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
def get(tag='__all__', limit=None, min_ts=None, max_ts=None):
    """
    Get all records from the store

    Log records are returned in the reverse time order (latest first)

    :param tag: if not equal to "__all__", then return only records marked with
                the corresponding tag
    :param limit: return at most this amount of records
    :param min_ts: optional minimum timestamp point
    :type min_ts: :class:`datetime.datetime` with optional tzinfo attached
    :param max_ts: optional maximum timestamp point
    :type max_ts: :class:`datetime.datetime` with optional tzinfo attached
    :rtype: min_ts of :class:`tagged_logger.Log`


    .. note:: Naive datetime objects are considered as having UTC tz and
              converted to seconds since epoch accordingly

    """
    return _logger.get(tag=tag, limit=limit, min_ts=min_ts, max_ts=max_ts)


@check_logger
def get_latest(tag='__all__'):
    """
    Get latest log record with a given tag or None

    :rtype: :class:`tagged_logger.Log`
    """
    return _logger.get_latest(tag=tag)


def log(message, tags=None, ts=None):
    """
    Create a new log record, optionally marked with one or more tags

    :type message: string or any jsonable object
    :type tags: list of strings
    :param ts: optional timestamp of the log record
    :type ts: :class:`datetime.datetime` object with optional timestamp set

    .. note:: Naive datetime objects are considered as having UTC tz and
              converted to seconds since epoch accordingly
    """
    return _logger.log(message, tags=tags, ts=ts)


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

    def log(self, message, tags=None, ts=None):
        _id = self._id()
        if ts is not None:
            timestamp = _dt2ts(ts)
        else:
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
        self.redis.zadd(flow_all, _id, timestamp)
        for tag in tags or []:
            flow_key = self._key('flow:{0}', tag)
            self.redis.zadd(flow_key, _id, timestamp)

    def get(self, tag='__all__', limit=None, min_ts=None, max_ts=None):
        key = self._key('flow:{0}', tag)

        max = _dt2ts(max_ts) if max_ts else float('inf')
        min = _dt2ts(min_ts) if min_ts else 0
        start = None if limit is None else 0

        record_ids = self.redis.zrevrangebyscore(key, max, min, start=start,
                                                 num=limit)
        if not record_ids:
            return []
        record_keys = [self._key('msg:{0}', _id) for _id in record_ids]
        records = self.redis.mget(record_keys)
        return [Log(record) for record in records]

    def get_latest(self, tag='__all__'):
        get_result = self.get(tag, limit=1)
        return get_result and get_result[0]

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


def _dt2ts(dt):
    """
    Convert datetime objects to correct timestamps

    Consider naive datetimes as UTC ones
    """
    if not dt.tzinfo:
        dt = pytz.utc.localize(dt)
    micro = dt.microsecond / 1e6
    ts = calendar.timegm(dt.timetuple())
    return ts + micro
