#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2020 Xvezda <xvezda@naver.com>
#
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re
import os
import sys
import json
import zipfile
import argparse
import requests

from os import path

import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


VERSION = '0.0.1'

if sys.version_info[0] < 3:
    input = raw_input


def urljoin(*args):
    return '/'.join(args)


class ViperError(Exception):
    pass


class BaseClient(object):
    def __init__(self):
        self._headers = {}

    @property
    def headers(self):
        return self._headers

    def update_headers(self, headers):
        self._headers.update(headers)


class ViperClient(BaseClient):
    BASE_URL = 'https://www.vim.org'
    USER_AGENT = 'viper/%s' % VERSION

    def __init__(self, username=None, password=None):
        super(ViperClient, self).__init__()
        self.update_headers({
            'User-Agent': self.USER_AGENT
        })

        self.username = username or os.getenv('VIPERS_USERNAME')
        self.password = password or os.getenv('VIPERS_PASSWORD')

        if (not sys.stdin.isatty()
                and (not self.username or not self.password)):
            raise ViperError('username or password required')

        if not self.username:
            self.username = input('username or email: ')

        if not self.password:
            import getpass
            self.password = getpass.getpass('password: ')

    def login(self):
        logger.debug('User-Agent: %s' % self.USER_AGENT)
        return
        self.update_headers({
            'Referer': urljoin(self.BASE_URL, 'login.php')
        })
        data = {
            'authenticate': 'true',
            'referrer': '',
            'userName': self.username,
            'password': self.password
        }
        r = requests.post(urljoin(self.BASE_URL, 'login.php'),
                          data=data, headers=self.headers,
                          allow_redirects=False)
        logger.info('%s, %s' % (r.text, r.headers))

        # Login failed
        if re.search('Authentication failed', r.text):
            raise ViperError('Authentication failed')

        self.update_headers({
            'Cookie': r.headers.get('Set-Cookie')
        })


def main():
    try:
        import dotenv
        dotenv.load_dotenv()
    except ImportError:
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help='set logging verbosity')

    subparsers = parser.add_subparsers(dest='command')
    build_parser = subparsers.add_parser('build')
    build_parser.add_argument('--output', '-o', default='dist')
    build_parser.add_argument('paths', nargs='+')

    publish_parser = subparsers.add_parser('publish')
    publish_parser.add_argument('--username', '-u')
    publish_parser.add_argument('--password', '-p')
    publish_parser.add_argument('--config', '-c',
                                help='set configuration file. '
                                'Default file is "vipers.json"',
                                default='vipers.json')
    clean_parser = subparsers.add_parser('clean')

    args = parser.parse_args()

    for path_ in args.paths:
        if not path.isdir(path_):
            parser.error('"%s" is not a directory' % path_)

    if args.verbose == 1:
        logger.setLevel(logging.INFO)
    elif args.verbose == 2:
        logger.setLevel(logging.DEBUG)

    client = ViperClient(username=args.username, password=args.password)
    client.login()


if __name__ == '__main__':
    main()

