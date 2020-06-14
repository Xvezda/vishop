#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2020 Xvezda <xvezda@naver.com>
#
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

from os import path

from setuptools import setup
from vipers import VERSION, AUTHOR, AUTHOR_EMAIL

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md')) as f:
    long_description = f.read()

setup(
    name='vipers',
    version=VERSION,
    description='Vipers is command line VIM script publisher client.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Xvezda/vipers',
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    classifiers=[
        'Environment :: Console',
        'Topic :: Text Editors',
        'Topic :: System :: Archiving :: Packaging',
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    entry_points='''
        [console_scripts]
        vipers=vipers:main
    ''',
    keywords='VIM VI plugin package manager utility publish',
    py_modules=['vipers'],
    install_requires=['requests'],
)
