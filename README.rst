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

There are a couple of notes you should take into consideration:

1. You can pass one additional tag parameter in there to filter out messages
2. Messages go in reverse time order, so the first message in :func:`get` will
   be the latest recorded one.
3. Every log record has a timestamp attached, the timestamp goes in UTC with a
   tz attribute attached
4. :class:`Log` objects have :func:`str` methods which simply call the str of
   the underlying object.

More filtering, formatting, expiration-related and other features coming soon.
Stay tuned.


Behind the scenes
-----------------

Tagged logger stores messages in Redis database. Every log message has unique
id, and this id (instead of the whole message itself) stores in several "flows",
identified by their tags;

Currently we use following keys:

- ``<prefix>:counter`` --- counter/generator of unique ids
- ``<prefix>:msg:<id>`` --- keys to store messages (messages are encoded in
  JSON format)
- ``<prefix>:flow:<tag>`` --- keys for flows for given tags
- ``<prefix>:flow:__all__`` --- key for a special flow storing all available log
  messages
