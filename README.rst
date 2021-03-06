Tagged logger
=============

Tagged logger is not a yet another logging module handler. Instead it's a fully
fledged package intended to store tagged log records into a Redis database.
Log records can be string messages with optional attributes and tags.

Usage
-----

Tags and attributes
````````````````````

The usage is pretty easy. Configure your logger with one function call, and then
go logging like crazy::

   >>> import tagged_logger as logger
   >>> logger.configure(prefix='my_tagged_logger')
   >>> logger.log('foo created', tags=['foo'])
   >>> logger.log('bar created', tags=['bar'])
   >>> logger.log('foo gets bar', tags=['foo', 'bar'])

You can attach one or more tags or attributes to messages. Upon handling tags
can be user to filter a subset of log records, and attributes can be
used to extract the structured information from a particular record::

   >>> logger.log('user logged in', user_id=1, user_login='u1')

All the kwargs, passed to :func:`log` will be stored as log record attributes,
in a separate field, json-encoded in the Redis database.

To get data from logger, use :func:`get` or :func:`get_latest` method::

   >>> logger.get()
   [<Log@...: u'foo gets bar'>, <Log@...: u'bar created'>, <Log@...: u'foo created'>]
   >>> logger.get('foo')
   [<Log@...: u'foo gets bar'>, <Log@...: u'foo created'>]
   >>> logger.get_latest('bar')
   <Log@...: u'foo gets bar'>


Function :func:`get` can have additional filters to get only a limited subset of
records. There are ``min_ts``, ``max_ts`` and ``limit`` options.

Formatting log record
`````````````````````

Sure enough, it's up to you to format the log record as you wish. The
:class:`Log` obejct has everything required for it. The following
list of fields can be found in there, and you are free to show the most
appropriate format.

- id: unique id of the record
- message: text message passed as the first parameter when message was created
- attrs: dict of attributes attached to the message
- tags: list of tags attached to the message
- ts: datetime object, containing the log record timestamp
- expire: datetime object, containing the log record expiration moment
  (or None of log record is marked as "everlasting")
- record: the "raw" JSON contents of the log records, as it is stored in the
  Redis database

Although there is a little helper we propose.

There is a :func:`__str__` method of the Log object which simply returns the
log string, but gf there are any attributes attached, the string is interpolated
with these attributes using "new style" python string substitution::

   >>> logger.log('{user_login} logged in', user_login='foo')
   >>> print str(logger.get_latest())
   foo logged in


Tagging attributes
``````````````````

Very often you'd like to use the same pair of key and value both for tags and
attributes. Tags are used to filter messages, whereas attributes are useful
for displaying them. That is, the recurring pattern looks like this::

   >>> ip='127.0.0.1'
   >>> logger.log('Received request from {ip}', ip=ip, tags=['ip:%s' % ip])

Then you can filter and print this message to see the following::

   >>> str(logger.get_latest('ip:127.0.0.1'))
   Received request from 127.0.0.1

To simplify your coding experience and life in general, tagged logger propose
the :class:`TaggingAttribute` class, which is the "attribute adding the tag to
the message also". You can create the class instance with the :func:`ta`
shortcut function, and pass this instance to :func:`log`, :func:`get` or
:func:`get_latest` methods. The prevoius example then is changed to something
different::

   >>> logger.log('Received request from {ip}', ta(ip='127.0.0.1'))

And then do::

   >>> logger.get_latest(ta(ip='127.0.0.1'))

Or just::

   >>> logger.get_latest(ip='127.0.0.1')

Please note, as you cannot filter by more than one tag, you cannot pass the
tagging attribute containing more that one attr to :func:`get` and
:func:`get_latest`.


Timestamps
``````````

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

Random notes
````````````

There are a couple of notes you should take into consideration:

1. Messages go in reverse time order, so the first message in :func:`get` will
   be the latest recorded one.
2. Every log record has a timestamp attached, the timestamp goes in UTC with a
   tz attribute attached


Context support
---------------

The hardest thing you should cope with in logging is saving context. Usually
it's a pain to store the context enough to write a complete and useful log message.
For example, while developing a web application, you'd like to store a remote
address of the request, probably the id of the authenticated client, if any,
and so forth.

In some web frameworks (for example, in Django) to do so you must drag the
Request object up and down throughout the stack (pass the data from the request,
down to the form, and then next to the overridden :func:`save` method of the
model).

To make the life easier, tagged logger offers the concept of context. You just
push your data or the tags you like to mark your message, to the context, and
then, all of a sudden, this extra data pops up to be saved along with your
message upon the log() invocation.

.. note:: it should be safe to use tagged logger in multithreaded environment,
          because logging contexts use thread locals.

Basically, there are two ways of working with context


Manual context injection
````````````````````````

It's a quite easy and straightforward way of doing stuff. Just use two pairs of
functions: :func:`add_tags` and :func:`rm_tags`, and :func:`add_attr`
and :func:`rm_attr`. To clean up everything, use :func:`reset_context`

For example, these two messages will be stored with tags "foo" and "bar"
attached::

    >>> logger.add_tags('foo', 'bar')
    >>> logger.save('Message one')
    >>> logger.save('Message two')

Similarly, every dict you log can be extended with a set of extra attributes.
It is safe to use plain string in messages, but in the latter case extra
attributes won't be stored with the log::

    >>> logger.add_attrs(remote_addr='127.0.0.1', user_id=123)
    >>> logger.save('Just a text')

You can add both tags and attributes at once, using tagging attributes::

   >>> logger.add_tagging_attrs(remote_addr='127.0.0.1', user_id=123)
   >>> logger.save('Just a text')

The difference between two cases above is that the latter one allows you to
filter by "remote_addr:127.0.0.1" and "user_id:123" tags.

At the end, don't forget to clean up the context::

    >>> logger.reset_context()


.. warning:: Be careful and don't forget to clean up the logger context after
             use (for example, at the end of the HTTP request). Otherwise your
             log data can leak out of control. Consider using context managers
             instead of add/rm functions. Remember, one thread of web
             application usually handles more than one HTTP request.

Using context managers
``````````````````````

It is safe and somewhat more convenient to use context manager instead of
manual injection of data. The list of args is considered as the list of tags
(or you can pass :class:`TaggingAttribute` instance here), whereas kwargs are
the attrs::

    >>> with logger.context('foo', remote_addr='127.0.0.1'):
    ...     logger.save('Object foo saved')


You can use nested context managers. Inner context managers will override or
extend the context of their outer counterparts.


Catching messages in real time
------------------------------

Tagged-logger takes advantage of Redis ability to effectively send broadcast
messages using the well-known publish-subscribe pattern.

It is very easy to create a logger instance listening and handling for log
message. The example is provided below::

   >>> logger.subscribe()
   >>> for message in logger.listen():
   ...     print message
   >>> logger.unsubscribe()

This naive example can easily be extended to a fully fledged twitter-alike web
service, yielding message from all your sources in the real time.

Expiration
----------

Because the tagged-logger is so incredibly fast and easy to use, you would
probably like to log much more than you used to log before. Some of these
log records may lose their value with time so fast, that you'd rather remove
periodically outdated records.

To simplify this, every record can be extended with the "expire" field. The
expiration field can be passed to :func:`log` function as integer
(expiration in seconds, since the time of the logging), timedelta (the same
meaning, but more convenient with bigger timespans) or as the absolute value
with the :class:`datetime.datetime` instance::

   >>> logger.log('expire in one hour', expire=3600)
   >>> logger.log('expire in one hour', expire=datetime.timedelta(hours=1))
   >>> logger.log('expire on the day of doom',
                   expire=datetime.datetime(2012, 12, 21))

Although the outdated records won't be removed automatically, and it's your
code which should periodically launch the cleaning process::

   >>> logger.expire()

Additionally, you would probably like not to remove these log messages, but
to archive them instead. In this case, you could pass additional optional
parameter to the function. This parameter is a callable which will be invoked
for every record just before the removal.

See the example below::

   >>> archive = []
   >>> def do_archive(record):
   ...     archive.append(record)
   >>> logger.expire(archive_func=do_archive)

Additionally, you can pass the :param:`archive_func` to the logger initializer::

   >>> logger.configure(archive_func=do_archive)


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
- ``<prefix>:flow:__expire__`` --- key for a special flow storing log messages
  to be removed on expiration.

Flow is based on sorted sets indexed by timestamp. That's why :func:`get`
operations with time-based limits are so fast (the processing time is estimated
as O(log n) where n is the total number of records in the flow).

The expiration flow uses expiration timestamps as the score value.
