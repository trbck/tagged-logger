# -*- coding: utf-8 -*-
import threading
import copy
import calendar
import json
import datetime
import pytz
import redis
import time

from functools import wraps
from contextlib import contextmanager
from string import Formatter


_logger = None
MISSING_KEY = '(undefined)'

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


def configure(prefix=None, archive_func=None, **redis_kwargs):
    """
    Configure logger

    :param prefix: prefix to store keys in redis database
    :param archive_func: callable which is about to be invoked on every expire
                         call
    :param \*\*redis_kwargs: arguments to be passed to Redis constructor
                             (`host`, `port` and `db` make sense)
    """
    global _logger
    if _logger:
        _logger.configure(prefix=prefix, archive_func=archive_func, **redis_kwargs)
    else:
        _logger = Logger(prefix=prefix, archive_func=archive_func, **redis_kwargs)
    return _logger


@check_logger
def full_cleanup():
    """
    Remove all records from the store
    """
    return _logger.full_cleanup()


@check_logger
def get(tag='__all__', limit=None, min_ts=None, max_ts=None, **kwargs):
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
    :param \*\*kwargs: the key-value pair used to build a tag. You cannot
                       user more than one key value pair, as it is possible
                       to filter message for at most one tag.
    :rtype: min_ts of :class:`tagged_logger.Log`


    .. note:: Naive datetime objects are considered as having UTC tz and
              converted to seconds since epoch accordingly

    """
    return _logger.get(tag=tag, limit=limit, min_ts=min_ts, max_ts=max_ts, **kwargs)


@check_logger
def get_latest(tag='__all__', **kwargs):
    """
    Get latest log record with a given tag or None

    :rtype: :class:`tagged_logger.Log`
    """
    return _logger.get_latest(tag=tag, **kwargs)


@check_logger
def log(message, *tagging_attrs, **attrs):
    """
    Create a new log record, optionally marked with one or more tags

    :param \*tagging_attrs: list of tagging attributes
    :type message: string or any jsonable object
    :type tags: list of strings
    :param ts: optional timestamp of the log record
    :type ts: :class:`datetime.datetime` object with optional timestamp set
    :param expire: optional expiration mark
    :type expire: :class:`datetime.datetime` object or :class:`datetime.timedelta`
              or :type:`int` (expiration in seconds since now)
    :param \*\*attrs: dictionary of log attributes to be stored in the
                      database

    .. note:: Naive datetime objects are considered as having UTC tz and
              converted to seconds since epoch accordingly
    """
    return _logger.log(message, *tagging_attrs, **attrs)


@check_logger
def context(*tags, **attrs):
    return _logger.context(*tags, **attrs)


@check_logger
def add_tags(*tags):
    return _logger.add_tags(*tags)


@check_logger
def rm_tags(*tags):
    return _logger.rm_tags(*tags)


@check_logger
def add_attrs(**attrs):
    return _logger.add_attrs(**attrs)


@check_logger
def rm_attrs(*attrs):
    return _logger.rm_attrs(*attrs)


@check_logger
def add_tagging_attrs(*tagging_attrs, **kwargs):
    return _logger.add_tagging_attrs(*tagging_attrs, **kwargs)


@check_logger
def rm_tagging_attrs(*tagging_attrs, **kwargs):
    return _logger.rm_tagging_attrs(*tagging_attrs, **kwargs)


@check_logger
def reset_context():
    return _logger.reset_context()


@check_logger
def subscribe():
    return _logger.subscribe()


@check_logger
def unsubscribe():
    return _logger.unsubscribe()


@check_logger
def listen():
    return _logger.listen()


@check_logger
def expire(archive_func=None, ts=None):
    return _logger.expire(archive_func=archive_func, ts=ts)


class Logger(object):

    def __init__(self, prefix=None, archive_func=None, **redis_kwargs):
        self.configure(prefix=prefix, archive_func=archive_func, **redis_kwargs)
        self._context = threading.local()

    def ensure_context(self):
        if not hasattr(self._context, 'tags'):
            self._context.tags = []
        if not hasattr(self._context, 'attrs'):
            self._context.attrs = {}
        if not hasattr(self._context, 'pubsub'):
            self._context.pubsub = self.redis.pubsub()

    def configure(self, prefix=None, archive_func=None, **redis_kwargs):
        self.prefix = prefix or ''
        self.archive_func = archive_func
        self.redis_kwargs = redis_kwargs
        self.redis = redis.Redis(**redis_kwargs)

    def full_cleanup(self):
        templates = ['msg:*', 'flow:*', 'counter']
        for tmpl in templates:
            keys = self.redis.keys(self._key(tmpl))
            if keys:
                self.redis.delete(*keys)

    def log(self, message, *tagging_attrs, **attrs):
        self.ensure_context()

        ts = attrs.pop('ts', None)
        tags = self._extend_tags(tagging_attrs, attrs.pop('tags', None))
        attrs = self._extend_attrs(tagging_attrs, attrs)
        expire = self._extend_expire(ts, attrs.pop('expire', None))

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
            'attrs': attrs,
            'tags': tags,
            'expire': _dt2ts(expire),
        }
        str_log_record = json.dumps(log_record_value)
        self.redis.set(log_record_key, str_log_record)
        # save log record reference to flows
        flow_all = self._key('flow:__all__')
        self.redis.zadd(flow_all, _id, timestamp)
        for tag in tags:
            flow_key = self._key('flow:{0}', tag)
            self.redis.zadd(flow_key, _id, timestamp)
        # add message to "expire" flow, if required
        if expire:
            expire_flow_key = self._key('flow:__expire__')
            expire_ts = _dt2ts(expire)
            self.redis.zadd(expire_flow_key, _id, expire_ts)
        # publish message
        pubsub_channel = self._key('log-records')
        self.redis.publish(pubsub_channel, str_log_record)

    def _extend_attrs(self, tagging_attrs, attrs):
        attrs = attrs.copy()
        for tagging_attr in tagging_attrs:
            attrs.update(tagging_attr.get_attrs())
        attrs.update(self._context.attrs)
        return attrs

    def _extend_tags(self, tagging_attrs, tags):
        ret = (tags or []) + self._context.tags
        for tagging_attr in tagging_attrs:
            ret += tagging_attr.get_tags()
        return list(set(ret))

    def _extend_expire(self, ts, expire):
        if expire is None:
            return None
        if isinstance(expire, datetime.datetime):
            return expire
        if isinstance(expire, datetime.timedelta):
            return ts + expire
        return ts + datetime.timedelta(seconds=expire)

    def get(self, tag='__all__', limit=None, min_ts=None, max_ts=None, **kwargs):

        if isinstance(tag, TaggingAttribute):
            kwargs = tag.get_attrs()

        if len(kwargs.keys()) > 1:
            raise RuntimeError('Unable to filter for more than one tag. The '
                               'filter expression is {0}'.format(kwargs))
        elif len(kwargs.keys()) == 1:
            key, value = list(kwargs.items())[0]
            tag = '{0}:{1}'.format(key, value)

        key = self._key('flow:{0}', tag)

        max = _dt2ts(max_ts) if max_ts else float('inf')
        min = _dt2ts(min_ts) if min_ts else 0
        start = None if limit is None else 0

        record_ids = self.redis.zrevrangebyscore(key, max, min, start=start,
                                                 num=limit)
        if not record_ids:
            return []
        record_keys = [self._key('msg:{0}', _id.decode('utf-8')) for _id in record_ids]
        records = self.redis.mget(record_keys)
        return [Log(record) for record in records]

    def get_latest(self, tag='__all__', **kwargs):
        get_result = self.get(tag, limit=1, **kwargs)
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

    @contextmanager
    def context(self, *tags, **attrs):
        self.ensure_context()
        old_tags = copy.copy(self._context.tags)
        old_attrs = self._context.attrs.copy()
        for tag in tags:
            if isinstance(tag, TaggingAttribute):
                self._context.tags += tag.get_tags()
                self._context.attrs.update(tag.get_attrs())
            else:
                self._context.tags.append(tag)
        self._context.attrs.update(attrs)
        try:
            yield
        finally:
            self._context.tags = old_tags
            self._context.attrs = old_attrs

    def add_tags(self, *tags):
        self.ensure_context()
        for tag in tags:
            if tag not in self._context.tags:
                self._context.tags.append(tag)

    def rm_tags(self, *tags):
        self.ensure_context()
        for tag in tags:
            if tag in self._context.tags:
                self._context.tags.remove(tag)

    def add_attrs(self, **attrs):
        self.ensure_context()
        self._context.attrs.update(attrs)

    def rm_attrs(self, *attrs):
        self.ensure_context()
        for attr in attrs:
            self._context.attrs.pop(attr, None)

    def add_tagging_attrs(self, *tagging_attrs, **kwargs):
        if kwargs:
            tagging_attrs = list(tagging_attrs) + [TaggingAttribute(**kwargs)]
        for tagging_attr in tagging_attrs:
            self.add_tags(*tagging_attr.get_tags())
            self.add_attrs(**tagging_attr.get_attrs())

    def rm_tagging_attrs(self, *tagging_attrs, **kwargs):
        if kwargs:
            tagging_attrs = list(tagging_attrs) + [TaggingAttribute(**kwargs)]
        for tagging_attr in tagging_attrs:
            self.rm_tags(*tagging_attr.get_tags())
            self.rm_attrs(*tagging_attr.get_attrs().keys())

    def reset_context(self):
        self._context.attrs = {}
        self._context.tags = []

    def subscribe(self):
        self.ensure_context()
        pubsub_channel = self._key('log-records')
        self._context.pubsub.subscribe(pubsub_channel)

    def unsubscribe(self):
        self.ensure_context()
        self._context.pubsub.unsubscribe()

    def listen(self):
        self.ensure_context()
        for message in self._context.pubsub.listen():
            if message['type'] == 'message':
                data = message['data']
                yield Log(data)

    def expire(self, archive_func=None, ts=None):
        ts = _dt2ts(ts) if ts else time.time()
        flow_expire = self._key('flow:__expire__')
        flow_all = self._key('flow:__all__')

        record_ids = self.redis.zrevrangebyscore(flow_expire, ts, 0)
        if not record_ids:
            return 0
        record_msgs = [self._key('msg:{0}', _id.decode('utf-8')) for _id in record_ids]

        records = self.redis.mget(*record_msgs)
        pipe = self.redis.pipeline()
        for record in records:
            record_obj = Log(record)
            if archive_func and callable(archive_func):
                archive_func(record_obj)
            elif self.archive_func and callable(self.archive_func):
                self.archive_func(record_obj)
            pipe.zrem(flow_all, record_obj.id)
            for tag in record_obj.tags:
                flow = self._key('flow:{0}'.format(tag))
                pipe.zrem(flow, record_obj.id)
        pipe.zremrangebyscore(flow_expire, 0, ts)
        pipe.delete(*record_msgs)
        pipe.execute()
        return len(records)


class TaggingAttribute(object):

    def __init__(self, **attrs):
        self.attrs = attrs

    def get_tags(self):
        return ['{0}:{1}'.format(*kv) for kv in self.attrs.items()]

    def get_attrs(self):
        return self.attrs


ta = TaggingAttribute


class Log(object):


    def __init__(self, record_str):
        record = json.loads(record_str.decode('utf-8'))
        self.id = record['id']
        self.message = record['message']
        self.attrs = record['attrs']
        self.tags = record['tags']
        self.ts = datetime.datetime.fromtimestamp(record['ts'], pytz.utc)
        if record['expire']:
            self.expire = datetime.datetime.fromtimestamp(record['expire'],
                                                          pytz.utc)
        else:
            self.expire = None
        self.record = record

    def __str__(self):
        formatter = LogFormatter()
        return str(formatter.vformat(self.message, (), self.attrs))

    def __unicode__(self):
        formatter = LogFormatter()
        return unicode(formatter.vformat(self.message, (), self.attrs))

    def __repr__(self):
        return '<Log@%s: %r attrs=%r tags=%r>' % (self.ts, self.message,
                                                  self.attrs, self.tags)


class LogFormatter(Formatter):

    def get_value(self, key, args, kwargs):
        try:
            return Formatter.get_value(self, key, args, kwargs)
        except KeyError:
            return MISSING_KEY

    def check_unused_args(self, used_args, args, kwargs):
        self.unused_args = {}
        for k, v in kwargs.items():
            if k not in used_args:
                self.unused_args[k] = v

    def vformat(self, format_string, args, kwargs):
        self.unused_args = {}
        ret = Formatter.vformat(self, format_string, args, kwargs)
        if not self.unused_args:
            return ret
        extra_data =  ', '.join('{0}={1}'.format(*kv) for kv in self.unused_args.items())
        return '{0} ({1})'.format(ret, extra_data)

def _dt2ts(dt):
    """
    Convert datetime objects to correct timestamps

    Consider naive datetimes as UTC ones
    """
    if dt is None:
        return dt
    if not dt.tzinfo:
        dt = pytz.utc.localize(dt)
    micro = dt.microsecond / 1e6
    ts = calendar.timegm(dt.timetuple())
    return ts + micro
