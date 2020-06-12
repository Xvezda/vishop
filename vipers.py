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

import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', help='Set configuration file. Default file is "vipers.json"')
    parser.add_argument('paths', nargs='+')
    args = parser.parse_args()


if __name__ == '__main__':
    main()

