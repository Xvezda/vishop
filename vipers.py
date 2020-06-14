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
AUTHOR = 'Xvezda'
AUTHOR_EMAIL = 'xvezda@naver.com'

if PY2:
    input = raw_input

def u(text):
    if PY2:
        return unicode(text).encode('utf8')
    return text


def urljoin(*args):
    return '/'.join(args)


def confirm(message):
    answer = input(message)
    if answer.lower().startswith('y'):
        return True
    return False


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
    config = {}
    require_fields = [
        'name',
        'type',
        'required',
        'init_version',
        'summary',
        'description'
    ]

    fields = require_fields + [
        'install_details'
    ]

    if any(not getattr(args, field, None) for field in require_fields):
        if not sys.stdin.isatty():
            print('init failed! there are empty fields', file=sys.stderr)
            return 1
        for field in fields:
            value = getattr(args, field, None)
            if not value:
                is_optional = field not in require_fields
                while not value:
                    try:
                        value = input('%s: ' % (field.replace('_', ' ')
                                      + (' (optional)' if is_optional else '')))
                    except KeyboardInterrupt:
                        print('cancel', file=sys.stderr)
                        return 1
                    if is_optional:
                        break
            config[field] = value
    print(config)


def build(args):
    logger.info('collecting files...')
    config = parse_config(args.config)

    files = []
    for path_ in (args.path or [] + args.paths):
        if not path.isdir(path_):
            raise ViperError('"%s" is not a directory' % path_)
        for dirpath, dirnames, filenames in os.walk(path_):
            for item in filenames:
                if item.startswith('.'):
                    continue
                files.append(path.join(dirpath, item))

    # Remove redundant duplicated files
    files = set(filter(path.normpath, files))

    # Exclude items
    if config.get('excludes') or args.exclude:
        excludes = config.get('excludes', []) + args.exclude or []
        def unescape(pattern, keywords):
            for keyword in keywords:
                pattern = pattern.replace('\\%s' % keyword, keyword)
            return pattern

        def escape(pattern):
            return unescape(re.escape(pattern), ['**', '*', '?'])
        # Escape patterns
        filters = map(escape, excludes)
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
    logger.debug('files: %s' % files)

    logger.info('parsing configuration')
    def bundle_name(config):
        return '%s-%s.%s' % (
            config.get('name', 'untitled').replace(' ', '-'),
            config.get('version', '0.1'),
            args.type
        )

    if not args.type:
        raise ViperError('type must be specified')

    if args.interactive:
        print('following files will be archived')
        print()

        files.sort()
        print('\n'.join(files[:args.limit]))

        if len(files) > args.limit:
            print()
            print('...and', len(files) - args.limit, 'more files!')

        print()
        print()
        if confirm('would you like to continue? [(y)es/(n)o]: '):
            pass
        else:
            return 1

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
    import shutil
    if (args.interactive
            and not confirm('"%s" will be deleted. are you sure? [(y)es/(n)o]: '
                            % args.path)):
        return 1
    shutil.rmtree(args.path, ignore_errors=True)
    print('Done!')


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
    init_parser.add_argument('--name', '-n')
    init_parser.add_argument('--type', '-t',
                             choices=[
                                 'color scheme',
                                 'ftplugin',
                                 'game',
                                 'indent',
                                 'syntax',
                                 'utility',
                                 'patch'])
    init_parser.add_argument('--required', '-r',
                             type=str,
                             default='7.0',
                             choices=[
                                 "5.7",
                                 "6.0",
                                 "7.0",
                                 "7.2",
                                 "7.3",
                                 "7.4",
                                 "8.0"])
    init_parser.add_argument('--init-version', '-V', type=str, default='1.0')
    init_parser.add_argument('--summary', '-s', type=str)
    init_parser.add_argument('--description', '-d', type=str)
    init_parser.add_argument('--install-details', '-D', type=str)
    init_parser.set_defaults(func=init)

    build_parser = subparsers.add_parser('build', parents=[common_parser],
                                         help='create plugin bundle to publish')
    build_parser.add_argument('--interactive', '-i', action='store_true')
    build_parser.add_argument('--limit', '-l',
                              type=int,
                              default=10,
                              help='limit of interactive information limits. '
                                   'ignored when interactive option disabled.')
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

    # TODO: Option for non-build publishing
    publish_parser = subparsers.add_parser('publish',
                                           help='publish plugin')
    publish_parser.add_argument('--username', '-u')
    publish_parser.add_argument('--password', '-p')
    publish_parser.set_defaults(func=publish)

    clean_parser = subparsers.add_parser('clean')
    clean_parser.add_argument('--interactive', '-i', action='store_true')
    clean_parser.add_argument('--path', '-p', type=str, default='dist')
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

