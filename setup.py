# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='tagged-logger',
    description=('Fast and flexible logger for Redis backend with tag'
                 'support'),
    author='Roman Imankulov',
    author_email='roman.imankulov@gmail.com',
    url='http://github.com/imankulov/tagged-logger',
    packages=['tagged_logger', ],
    version='0.5',
    license='BSD',
    scripts=[
        'scripts/tagged_logger_listen.py',
        'scripts/tagged_logger_get.py',
    ],
    install_requires=[
        'redis',
        'pytz',
    ],
)
