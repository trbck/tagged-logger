Tagged logger
=============

Tagged logger is not a yet another logging module handler. Instead it's a fully
fledged package intended to store tagged log records into a Redis database.
Log records can be string messages or any old jsonable objects.

Usage
-----

The usage is pretty easy. Configure your logger with one function call, and then
go logging like crazy::

   >>> import tagged_logger as logger
   >>> logger.configure(prefix='my_tagged_logger')
   >>> logger.log('foo created', tags=['foo'])
   >>> logger.log('bar created', tags=['bar'])
   >>> logger.log('foo gets bar', tags=['foo', 'bar'])

To get data from logger, use :func:`get` or :func:`get_latest` method::

   >>> logger.get()
   [<Log@...: u'foo gets bar'>, <Log@...: u'bar created'>, <Log@...: u'foo created'>]
   >>> logger.get('foo')
   [<Log@...: u'foo gets bar'>, <Log@...: u'foo created'>]
   >>> logger.get_latest('bar')
   <Log@...: u'foo gets bar'>

Function :func:`get` can have additional filters to get only a limited subset of
records. There are ``min_ts``, ``max_ts`` and ``limit`` options.

As logger uses UTC as the reference point for all timestamps, you could use it
too.

For example::

   >>> logger.log('foo gets bar')
   >>> logger.get(min_ts=datetime.datetime.now() - datetime.timedelta(seconds=60))

very likely returns nothing, depending on which timezone you live in. Instead,
you should use::

   >>> logger.log('foo gets bar')
   >>> logger.get(min_ts=datetime.datetime.utcnow() - datetime.timedelta(seconds=60))

Mind the :function:`utcnow` method name.

There are a couple of notes you should take into consideration:


1. Messages go in reverse time order, so the first message in :func:`get` will
   be the latest recorded one.
2. Every log record has a timestamp attached, the timestamp goes in UTC with a
   tz attribute attached
3. :class:`Log` objects have :func:`str` methods which simply call the str of
   the underlying object.

More filtering, formatting, expiration-related and other features coming soon.
Stay tuned.


Behind the scenes
-----------------

Tagged logger stores messages in Redis database. Every log message has unique
id, and this id (instead of the whole message itself) stores in several "flows",
identified by their tags. Currently we use following keys:

- ``<prefix>:counter`` --- counter/generator of unique ids
- ``<prefix>:msg:<id>`` --- keys to store messages (messages are encoded in
  JSON format)
- ``<prefix>:flow:<tag>`` --- keys for flows for given tags.
- ``<prefix>:flow:__all__`` --- key for a special flow storing all available log
  messages

Flow is based on sorted sets indexed by timestamp. That's why :func:`get`
operations with time-based limits are so fast (the processing time is estimated
as O(log n) where n is the total number of records in the flow).
