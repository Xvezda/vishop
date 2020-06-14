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

import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())

from version import VERSION, AUTHOR, AUTHOR_EMAIL

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

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


def wildcard(pattern):
    # NOTE: Do not use replace character in replacement string
    #       It will cause nasty bug
    #       (e.g. use `{0,}` instead of `*`)
    return (pattern
        .replace('**', r'[\s\S]{0,}')
        .replace('*', '[^%s]{0,}' % re.escape(os.path.sep))
        .replace('?', '[^%s]?' % re.escape(os.path.sep)))


def unescape(pattern, keywords):
    for keyword in keywords:
        pattern = pattern.replace('\\%s' % keyword, keyword)
    return pattern


def escape(pattern):
    return unescape(re.escape(pattern), ['**', '*', '?'])


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

    def __init__(self, args=None):
        super(ViperClient, self).__init__()
        self.update_headers({
            'User-Agent': self.USER_AGENT
        })

        self.args = args

        self.username = args.username or os.getenv('VIPERS_USERNAME')
        self.password = args.password or os.getenv('VIPERS_PASSWORD')

        if (not sys.stdin.isatty()
                and (not self.username or not self.password)):
            raise ViperError('username or password required')

        if not self.username:
            self.username = input('username or email: ')

        if not self.password:
            import getpass
            self.password = getpass.getpass('password: ')

    def login(self):
        print('attempt to login...')
        logger.debug('User-Agent: %s' % self.USER_AGENT)
        self.update_headers({
            'Referer': urljoin(self.BASE_URL, 'login.php')
        })
        data = {
            'authenticate': 'true',
            'referrer': '',
            'userName': self.username,
            'password': self.password
        }
        url = urljoin(self.BASE_URL, 'login.php')
        r = requests.post(url,
                          data=data, headers=self.headers,
                          allow_redirects=False)
        self.update_headers({
            'Cookie': r.headers.get('Set-Cookie'),
            'Referer': url
        })
        url = r.headers.get('Location')
        r = requests.get(url,
                         headers=self.headers)
        logger.info('%s, %s' % (r.text, r.headers))
        self.update_headers({
            'Referer': url
        })

        # Login failed
        if re.search('Authentication failed', r.text):
            raise ViperError('authentication failed')
        print('login success!')

    def publish(self):
        config = parse_config(self.args.config)
        description = self.args.description or config.get('description')
        if not description:
            # TODO: Find README* files
            wildcard_filter = lambda x: re.match(wildcard(escape('README*')), x)
            files = list(filter(wildcard_filter, os.listdir('.')))
            if not files:
                raise ViperError('description required')
            with open(files[0], 'rt') as f:
                description = f.read()
        # Form data
        data = {
            'ACTION': 'UPLOAD_NEW',
            'MAX_FILE_SIZE': '10485760',
            'script_name': config.get('name'),
            # 'script_file': None,  # binary
            'script_type': config.get('type'),
            'vim_version': config.get('required'),
            'script_version': config.get('version'),
            'summary': config.get('summary'),
            'description': description,
            'install_details': config.get('install_details', ''),
            'add_script': 'upload'
        }
        files = {'script_file': open(self.args.file, 'rb')}
        url = urljoin(self.BASE_URL, 'scripts', 'add_script.php')

        if (self.args.interactive
                and not confirm('"%s" [(y)es/(n)o]: ' % self.args.file)):
            return

        logger.debug('data: %s' % data)
        print('uploading...')

        r = requests.post(url, data=data, files=files, headers=self.headers,
                          allow_redirects=False)

        logger.debug('text: %s' % r.text)
        logger.debug('headers: %r' % r.headers)
        logger.debug('status_code: %r' % r.status_code)

        if r.status_code != 302:
            print('something goes wrong', file=sys.stderr)
            return 1
        print('Done!')

        result_url = r.headers.get('Location')
        print('URL:', result_url)


def parse_config(config):
    with open(config, 'r') as f:
        return json.load(f)


def init(args):
    config = {}
    fields = [
        {'name': 'name'},
        {
            'name': 'type',
            'type': str,
            'choices': [
                'color scheme',
                 'ftplugin',
                 'game',
                 'indent',
                 'syntax',
                 'utility',
                 'patch'
            ]
        },
        {'name': 'required'},
        {'name': 'init_version', 'alias': 'version'},
        {'name': 'summary'},
        {'name': 'description', 'optional': True},
        {'name': 'install_details', 'optional': True},
        {'name': 'private', 'type': bool, 'optional': True, 'default': False}
    ]

    # Exit if required parameters empty and not interactive
    if (any(not field.get('optional', None)
            and not getattr(args, field.get('name'), None) for field in fields)
            and not sys.stdin.isatty()):
        print('init failed! there are empty fields', file=sys.stderr)
        return 1

    def create_label(field, indent=4, indent_char=' '):
        name = field.get('name')
        output = name.replace('-', ' ').replace('_', ' ')
        optional = field.get('optional', None)
        choices = field.get('choices', None)
        if optional or choices:
            if optional:
                output += ' (optional)'
            if choices:
                for choice in choices:
                    output += '\n'
                    output += indent_char * indent
                    output += choice
                output += '\n'
                output += 'select %s' % name
        return output

    for field in fields:
        name = field.get('name')
        value = getattr(args, name, None)
        if not value:
            is_optional = field.get('optional', None)
            choices = field.get('choices', None)
            while (not value
                   or (choices and value not in choices)):
                label = create_label(field)
                try:
                    value = input('%s: ' % label)
                except KeyboardInterrupt:
                    print('cancel', file=sys.stderr)
                    return 1
                field_type = field.get('type', None)
                if field_type:
                    # Bool exception
                    if field_type is bool and value.lower() == 'false':
                        value = False
                    else:
                        value = field_type(value)
                if is_optional:
                    break
            if is_optional and not value:
                continue
        alias = field.get('alias', name)
        config[alias] = value
    print()

    reversed_config = {}
    for k, v in config.items():
        reversed_config[k] = v

    with open(args.output, 'w') as f:
        json.dump(reversed_config, f,
                  indent=4, separators=(',', ': '))
    print('Done!')


def build(args):
    logger.info('collecting files...')
    config = parse_config(args.config)

    files = []
    for path in (args.path or [] + args.paths):
        if not os.path.isdir(path):
            raise ViperError('"%s" is not a directory' % path)
        for dirpath, dirnames, filenames in os.walk(path):
            for item in filenames:
                if item.startswith('.'):
                    continue
                files.append(os.path.join(dirpath, item))

    # Remove redundant duplicated files
    files = set(filter(os.path.normpath, files))

    # Exclude items
    if config.get('excludes') or args.exclude:
        excludes = config.get('excludes', []) + args.exclude or []
        # Escape patterns
        filters = map(escape, excludes)
        # Remove empty exclude patterns
        filters = filter(lambda x: x, filters)
        # Prefix recursive wildcard
        def prefix(exclude):
            if exclude.startswith('**'):
                return exclude
            return '**%s' % os.path.sep + exclude
        # Support wildcards
        filters = map(wildcard, map(prefix, filters))

        # Convert non list variables to list
        filters = list(filters)
        files = list(files)

        # Filter it
        filtered = []
        for file_ in files:
            for pattern in filters:
                formatted = '^({0}{1}|{0}$)'.format(pattern, os.path.sep)
                logger.debug(
                    '%r %r %r' % (formatted,
                                  file_,
                                  bool(re.match(formatted, file_))))
                if re.match(formatted, file_):
                    break
            else:
                filtered.append(file_)
        files = filtered
    files = list(files)
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

    if not files:
        raise ViperError('at least 1 file required')

    if args.interactive:
        print('following files will be archived')
        print()

        # files = sorted(files)
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

    bundle_path = os.path.join(args.output, bundle_name(config))
    try:
        os.makedirs(os.path.dirname(bundle_path))
    except OSError:
        # Already exists
        pass

    import tarfile
    import zipfile

    if args.type.startswith('tar'):
        # mode = ''
        # if args.type == 'tar':
        #     mode = 'w'
        # else:
        #     mode = 'w:%s' % args.type.split('.')[-1]
        with tarfile.TarFile(bundle_path, 'w',
                             format=tarfile.GNU_FORMAT) as f:
            for file_ in files:
                f.add(file_)
    elif args.type == 'zip':
        with zipfile.ZipFile(bundle_path, 'w') as f:
            for file_ in files:
                f.write(file_)

    print('Done!')


def publish(args):
    client = ViperClient(args)
    client.login()
    client.publish()


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
    init_parser = subparsers.add_parser('init', parents=[common_parser],
                                        help='create configuration file')
    init_parser.add_argument('--output', '-o',
                             type=str,
                             default='vipers.json')
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
    init_parser.add_argument('--private', '-p', type=bool, default=False)
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
    # TODO: Add format selection for tar files (e.g. POSIX, GNU...).
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
    #       Use README* file for description
    publish_parser = subparsers.add_parser('publish', parents=[common_parser],
                                           help='publish plugin')
    publish_parser.add_argument('--username', '-u')
    publish_parser.add_argument('--password', '-p')
    publish_parser.add_argument('--description', '-d')
    publish_parser.add_argument('--interactive', '-i', action='store_true')
    publish_parser.add_argument('file', type=str)
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

    if not args.command:
        parser.error('too few arguments')

    # Exceptions
    if args.command == 'build':
        try:
            if args.file or args.path or args.paths:
                pass
            else:
                raise AttributeError
        except AttributeError:
            build_parser.error('at least one file or path required')

    args.func(args)


if __name__ == '__main__':
    main()

