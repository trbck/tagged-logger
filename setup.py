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
    classifiers=(
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: System :: Logging',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
    ),
)
