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
import tarfile
import zipfile

import requests  # noqa
from bs4 import BeautifulSoup  # noqa

import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())

from .__version__ import __version__, __author__, __email__  # noqa

CONFIG_FILENAME = 'vipers.json'

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY2:
    input = raw_input  # noqa

def u(text):
    if PY2:
        return unicode(text).encode('utf8')  # noqa
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
    USER_AGENT = 'viper/%s' % __version__
    MAX_FILE_SIZE = '10485760'

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
    
    def config_from_bundle(self, path):
        if re.search(r'\.tar\.[a-z]+$', path):  # tar file
            with tarfile.TarFile(path, 'r') as f:
                filtered = filter(lambda x: x.endswith(self.args.config), f.getnames())
                config_name = sorted(list(filtered), key=len)[0]
                return json.loads(f.extractfile(config_name).read())
        elif re.search(r'\.zip$', path):  # zip file
            with zipfile.ZipFile(path, 'r') as f:
                return json.loads(f.read(self.args.config))
        raise ViperError("file '%s' is not supported type" % path)

    def login(self):
        print('attempt to login...')
        logger.debug('User-Agent: %s' % self.USER_AGENT)

        url = urljoin(self.BASE_URL, 'login.php')
        self.update_headers({
            'Referer': url
        })
        data = {
            'authenticate': 'true',
            'referrer': '',
            'userName': self.username,
            'password': self.password
        }
        r = requests.post(url,
                          data=data, headers=self.headers,
                          allow_redirects=False)
        self.update_headers({
            'Cookie': r.headers.get('Set-Cookie'),
            'Referer': url
        })

        logger.debug('headers: %r' % r.headers.get('Location'))
        logger.debug('text: %s' % r.text)
        logger.debug('status_code: %d' % r.status_code)

        # Exception
        if r.status_code == 200:
            if re.search('try again later', r.text):
                raise ViperError('maximum quota exceeded: %s' % r.text)
            raise ViperError('unexpected exception occurred')

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

    def info(self):
        information = self.fetch_info()

        print('user name:', information.get('user_name'))
        print('first name:', information.get('first_name'))
        print('last name:', information.get('last_name'))
        print('email:', information.get('email'))

        print('scripts:')
        for script in information.get('scripts', []):
            print(' '*2 + '%s: %s' % (script.get('name'), script.get('summary')))

    def fetch_info(self):
        ret = {}
        # https://www.vim.org/account/index.php
        url = urljoin(self.BASE_URL, 'account', 'index.php')
        r = requests.get(url, headers=self.headers)
        self.update_headers({
            'Referer': url
        })
        if r.status_code != 200:
            raise ViperError('error occurred while fetching account informations')
        html = BeautifulSoup(r.text, 'html.parser')

        ret['user_name'] = html.find('td', string='user name').find_next_sibling('td').string
        ret['first_name'] = html.find('td', string='first name').find_next_sibling('td').string
        ret['last_name'] = html.find('td', string='last name').find_next_sibling('td').string
        ret['email'] = html.find('td', string='email').find_next_sibling('td').string
        # ret['homepage'] = html.find('td', string='homepage').find_next_sibling('td').string

        contrib_title = html.find('h1', string='Script Contributions')
        if not contrib_title:
            raise ViperError('unexpected error occurred: cannot find contribute title')
        contrib_table = contrib_title.find_next_sibling('table')

        def get_id_by_url(url):
            id_match = re.search(r'script_id=(\d+)', url)
            if not id_match:
                raise ViperError('cannot find script id')
            return id_match.group(1)

        scripts = []
        for row in contrib_table.find_all('tr'):
            name, summary, _, _ = row.find_all('td')
            script_href = name.find('a')['href']
            script_id = get_id_by_url(script_href)
            scripts.append({
                'id': script_id,
                'name': name.string,
                'summary': summary.string
            })
        ret['scripts'] = scripts
        return ret

    def fetch_scripts(self):
        info = self.fetch_info()
        return info['scripts']

    def versions(self, script_id):
        # https://www.vim.org/scripts/script.php?script_id=[id]
        url = urljoin(self.BASE_URL, 'scripts', 'script.php?script_id=%d' % int(script_id))
        r = requests.get(url, headers=self.headers)
        self.update_headers({
            'Referer': url
        })
        if r.status_code != 200:
            raise ViperError('error occurred while fetching script detail')
        html = BeautifulSoup(r.text, 'html.parser')
        error_header = html.find('p', class_='errorheader')
        if error_header:
            raise ViperError(error_header.find_next_sibling('p').string)
        script_table = html.find('th', string='package').find_parent('table')
        ret = []
        for row in script_table.find_all('tr')[1:]:  # Skip header
            package, version, date, required, user, note = row.find_all('td')
            ret.append(version.string)
        return ret

    def script_version(self, script_id):
        url = urljoin(self.BASE_URL, 'scripts', 'add_script_version.php?script_id=%d' % int(script_id))
        r = requests.get(url, headers=self.headers)
        self.update_headers({
            'Referer': url
        })
        if r.status_code != 200:
            raise ViperError('error occurred while fetching script detail')
        html = BeautifulSoup(r.text, 'html.parser')
        heading = html.find('h1', string=re.compile('Upload a new version of'))
        version = heading.find_next_sibling('p').string.strip().split(' ')[-1]
        return version

    def update(self, file):
        if not sys.stdin.isatty():
            raise ViperError('update must be interactive mode')

        scripts = self.fetch_scripts()

        def find_id(name):
            for script in scripts:
                if script.get('name') == name:
                    return script.get('id')

        config = self.config_from_bundle(file)

        script_id = find_id(config.get('name'))
        logger.debug('id: %s' % script_id)

        comment = ''
        while not comment:
            try:
                comment = input('version comment: ')
            except KeyboardInterrupt:
                print('cancel', file=sys.stderr)
                sys.exit(1)

        data = {
            'MAX_FILE_SIZE': self.MAX_FILE_SIZE,
            'vim_version': config.get('required'),
            'script_version': config.get('version'),
            'version_comment': comment,
            'script_id': script_id,
            'add_script': 'upload'
        }
        files = {'script_file': open(file, 'rb')}
        # https://www.vim.org/scripts/add_script_version.php?script_id=[id]
        url = urljoin(self.BASE_URL, 'scripts', 'add_script_version.php?script_id=%s' % script_id)
        logger.debug('url: %s' % url)
        logger.debug('data: %r' % data)

        versions = self.versions(script_id)
        logger.debug('versions: %r' % versions)

        version = config.get('version')
        if version in versions:
            raise ViperError("cannot update script: version '%s' already exists!" % version)
            # return

    def upload(self, file):
        config = self.config_from_bundle(file)
        description = self.args.description or config.get('description')
        if not description:
            wildcard_filter = lambda x: re.match(wildcard(escape('README*')), x)
            files = list(filter(wildcard_filter, os.listdir('.')))
            if not files:
                raise ViperError('description required')
            with open(files[0], 'rt') as f:
                description = f.read()
        # Form data
        data = {
            'ACTION': 'UPLOAD_NEW',
            'MAX_FILE_SIZE': self.MAX_FILE_SIZE,
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
        files = {'script_file': open(file, 'rb')}
        url = urljoin(self.BASE_URL, 'scripts', 'add_script.php')

        if (self.args.interactive
                and not confirm('"%s" [(y)es/(n)o]: ' % file)):
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

    def publish(self):
        for file in self.args.files:
            config = self.config_from_bundle(file)
            name = config.get('name')

            scripts = self.fetch_scripts()
            if scripts and any(name == script.get('name') for script in scripts):
                self.update(file)
            else:
                pass  # FIXME: Remove comment
                # self.upload(file)


def parse_config(config):
    with open(config, 'r') as f:
        return json.load(f)


def _init_command(args):
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


def _info_command(args):
    client = ViperClient(args)
    client.login()
    client.info()


def _build_command(args):
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


def _publish_command(args):
    client = ViperClient(args)
    client.login()
    client.publish()


def _clean_command(args):
    import shutil
    if (args.interactive
            and not confirm('"%s" will be deleted. are you sure? [(y)es/(n)o]: '
                            % args.path)):
        return 1
    shutil.rmtree(args.path, ignore_errors=True)
    print('Done!')


def main():
    try:
        import dotenv  # noqa
        dotenv.load_dotenv()
    except ImportError:
        pass


    import argparse
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument('--verbose', '-v', action='count', default=0,
                               help='set logging verbosity')
    common_parser.add_argument('--config', '-c',
                               help='set configuration file name. '
                               'Default file is "%s"' % CONFIG_FILENAME,
                               default=CONFIG_FILENAME)

    parser = argparse.ArgumentParser(parents=[common_parser])
    subparsers = parser.add_subparsers(dest='command')

    # TODO: We need interactive interface
    init_parser = subparsers.add_parser('init', parents=[common_parser],
                                        help='create configuration file')
    init_parser.add_argument('--output', '-o',
                             type=str,
                             default=CONFIG_FILENAME)
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
    init_parser.set_defaults(func=_init_command)

    info_parser = subparsers.add_parser('info', parents=[common_parser],
                                        help='get informations from website')
    info_parser.add_argument('--username', '-u')
    info_parser.add_argument('--password', '-p')
    info_parser.set_defaults(func=_info_command)

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
                                  '__pycache__',
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
    build_parser.set_defaults(func=_build_command)

    # TODO: Option for non-build publishing
    #       Use README* file for description
    publish_parser = subparsers.add_parser('publish', parents=[common_parser],
                                           help='publish plugin')
    publish_parser.add_argument('--username', '-u')
    publish_parser.add_argument('--password', '-p')
    publish_parser.add_argument('--description', '-d')
    publish_parser.add_argument('--interactive', '-i', action='store_true')
    publish_parser.add_argument('files', action='append')
    publish_parser.set_defaults(func=_publish_command)

    clean_parser = subparsers.add_parser('clean')
    clean_parser.add_argument('--interactive', '-i', action='store_true')
    clean_parser.add_argument('--path', '-p', type=str, default='dist')
    clean_parser.set_defaults(func=_clean_command)

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
