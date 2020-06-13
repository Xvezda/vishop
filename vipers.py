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
import requests

from os import path

import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
VERSION = '0.0.1'

if PY2:
    input = raw_input

def u(text):
    if PY2:
        return unicode(text).encode('utf8')
    return text


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


def parse_config(config):
    with open(config, 'r') as f:
        return json.load(f)


def init(args):
    pass


def build(args):
    files = []
    for path_ in (args.path or [] + args.paths):
        if not path.isdir(path_):
            raise ViperError('"%s" is not a directory' % path_)
        for dirpath, dirnames, filenames in os.walk(path_):
            for item in filenames:
                if item.startswith('.'):
                    continue
                files.append(path.join(dirpath, item))
    # if args.file:
    #     files.extend(args.file)
    # if args.file:
    #     for a in args.file:
    #         for b in files:
    #             if path.samefile(a, b):
    #                 break
    #         else:
    #             files.append(a)

    # Remove redundant duplicated files
    files = set(filter(path.normpath, files))
    # rmidx = []
    # for i, a in enumerate(files):
    #     for j, b in enumerate(files):
    #         if j in rmidx or i == j or path.basename(a) == path.basename(b):
    #             continue
    #         if path.samefile(a, b):
    #             rmidx.append(j)
    # for idx in rmidx:
    #     files.remove(idx)

    # Exclude items
    if args.exclude:
        def unescape(pattern, keywords):
            for keyword in keywords:
                pattern = pattern.replace('\\%s' % keyword, keyword)
            return pattern

        def escape(pattern):
            return unescape(re.escape(pattern), ['**', '*', '?'])
        # Escape patterns
        filters = map(escape, args.exclude)
        # Remove empty exclude patterns
        filters = filter(lambda x: x, filters)
        # Prefix recursive wildcard
        def prefix(exclude):
            if exclude.startswith('**'):
                return exclude
            return '**%s' % path.sep + exclude
        filters = map(prefix, filters)

        # Support wildcards
        def wildcard(pattern):
            # NOTE: Do not use replace character in replacement string
            #       It will cause nasty bug
            #       (e.g. use `{0,}` instead of `*`)
            return (pattern
                .replace('**', r'[\s\S]{0,}')
                .replace('*', '[^%s]{0,}' % re.escape(path.sep))
                .replace('?', '[^%s]?' % re.escape(path.sep)))
        filters = map(wildcard, filters)

        # Filter it
        files = filter(
            lambda x: not any(
                re.match('^({0}$|{0}{1})'.format(
                    pattern, re.escape(path.sep)), x)
            for pattern in filters),
            files
        )

    config = parse_config(args.config)
    def bundle_name(config):
        return '%s-%s.%s' % (
            config.get('name', 'untitled').replace(' ', '-'),
            config.get('version', '0.1'),
            args.type
        )

    if not args.type:
        raise ViperError('type must be specified')

    bundle_path = path.join(args.output, bundle_name(config))
    try:
        os.makedirs(path.dirname(bundle_path))
    except OSError:
        # Already exists
        pass

    import tarfile
    import zipfile

    if args.type.startswith('tar'):
        mode = ''
        if args.type == 'tar':
            mode = 'w'
        else:
            mode = 'w:%s' % args.type.split('.')[-1]

        with tarfile.open(bundle_path, mode) as f:
            for file_ in files:
                f.add(file_)
    elif args.type == 'zip':
        with zipfile.ZipFile(bundle_path, 'w') as f:
            for file_ in files:
                f.write(file_)

    print('Done!')


def publish(args):
    client = ViperClient(username=args.username, password=args.password)
    client.login()


def clean(args):
    pass


def main():
    try:
        import dotenv
        dotenv.load_dotenv()
    except ImportError:
        pass


    import argparse
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument('--verbose', '-v', action='count', default=0,
                               help='set logging verbosity')
    common_parser.add_argument('--config', '-c',
                               help='set configuration file. '
                               'Default file is "vipers.json"',
                               default='vipers.json')

    parser = argparse.ArgumentParser(parents=[common_parser])
    subparsers = parser.add_subparsers(dest='command')

    # TODO: We need interactive interface
    init_parser = subparsers.add_parser('init',
                                        help='create configuration file')
    init_parser.set_defaults(func=init)

    # TODO: What about zip alternative formats? (i.e. tar.gz)
    build_parser = subparsers.add_parser('build', parents=[common_parser],
                                         help='create plugin bundle to publish')
    build_parser.add_argument('--ignore-file', '-n', default='.gitignore',
                              help='use ignore file to filter plugin items. '
                              'comma sperated ignore files '
                              '(default: ".gitignore")')
    build_parser.add_argument('--exclude', '-x', action='append',
                              default=[
                                  'dist',
                                  '.git',
                                  'venv',
                                  'node_modules',
                              ])
    build_parser.add_argument('--file', '-f', action='append')
    build_parser.add_argument('--path', '-p', action='append')
    build_parser.add_argument('--type', '-t',
                              default='tar.gz',
                              choices=[
                                  'tar.gz',
                                  'tar.bz2',
                                  'tar.xz',
                                  'zip'
                              ],
                              help='set output file type')
    build_parser.add_argument('--output', '-o', type=str, default='dist')
    build_parser.add_argument('paths', nargs='*')
    build_parser.set_defaults(func=build)

    # TODO: Show contents before publishing
    #       Option for non-build publishing
    publish_parser = subparsers.add_parser('publish',
                                           help='publish plugin')
    publish_parser.add_argument('--username', '-u')
    publish_parser.add_argument('--password', '-p')
    publish_parser.set_defaults(func=publish)

    clean_parser = subparsers.add_parser('clean')
    clean_parser.set_defaults(func=clean)

    args = parser.parse_args()

    # Set logger verbose level
    if args.verbose == 1:
        logger.setLevel(logging.INFO)
    elif args.verbose == 2:
        logger.setLevel(logging.DEBUG)

    # Exceptions
    if args.command == 'build':
        if not args.file and not args.path and not args.paths:
            build_parser.error('at least one file or path required')

    args.func(args)


if __name__ == '__main__':
    main()

