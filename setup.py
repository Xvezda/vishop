#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2020 Xvezda <xvezda@naver.com>
#
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

from os import path
from setuptools import setup, find_packages


here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'vishop', '__about__.py')) as f:
    exec(f.read())

with open(path.join(here, 'README.md')) as f:
    long_description = f.read()

setup(
    name='vishop',
    version=__version__,
    description='Vishop is command line VIM script publisher client.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    url='https://github.com/Xvezda/vishop',
    author=__author__,
    author_email=__email__,
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
        vishop=vishop.core:main
    ''',
    keywords='VIM, VI, editor, plugin, package manager, utility, publishing',
    packages=find_packages(),
    install_requires=['requests', 'BeautifulSoup4'],
    zip_safe=False
)
