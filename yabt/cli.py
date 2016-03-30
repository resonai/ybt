# -*- coding: utf-8 -*-

# Copyright 2016 Yowza Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
yabt cli module
~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import os

import argcomplete
import colorama
import configargparse

from .config import BUILD_PROJ_FILE, Config, YCONFIG_FILE


PARSER = None


def make_parser(project_config_file: str):
    global PARSER
    if PARSER is None:
        config_files = ['/etc/yabt.conf', '~/.yconfig']
        if project_config_file:
            config_files.append(project_config_file)
        PARSER = configargparse.getArgumentParser(
            # Support loading default values from system-wide or
            # user-specific config files (user-level overrides system-wide)
            default_config_files=config_files,
            # Show default values in help message
            formatter_class=configargparse.DefaultsFormatter,
            auto_env_var_prefix='ybt_',
            args_for_setting_config_path=['--config'],
            args_for_writing_out_config_file=['--write-out-config-file'])
        # PARSER.add('--config', is_config_file=True, help='Config file path')
        PARSER.add('--build-file-name', default='ybuild')
        PARSER.add('--default-target-name', default='@default')
        PARSER.add('--builders-workspace-dir', default='yabtwork')
        PARSER.add('cmd', choices=['build', 'tree', 'version'],
                   nargs='?', default='build')
        PARSER.add('targets', nargs='*')
    return PARSER


def find_project_base_dir(start_at: str=None):
    """Return absolute path of first parent directory of `start_at` that
       contains a file named `BUILD_PROJ_FILE` (including `start_at`).

    If `start_at` not specified, start at current working directory.

    :param start_at: Initial path for searching for the project build file.

    Raises OSError upon reaching FS root without finding anything.
    """
    if not start_at:
        start_at = os.path.abspath(os.curdir)
    while start_at:
        for entry in os.scandir(start_at):
            if entry.is_file() and entry.name == BUILD_PROJ_FILE:
                return start_at
        cur_level = start_at
        start_at = os.path.split(cur_level)[0]
        if os.path.realpath(cur_level) == os.path.realpath(start_at):
            # looped on root once
            raise IOError('Not a YABT project (or any of the parent '
                          'directories): {}'.format(BUILD_PROJ_FILE))


def init_and_get_conf(argv=None):
    colorama.init()
    work_dir = os.path.abspath(os.curdir)
    project_root = find_project_base_dir(work_dir)
    project_config_file = os.path.join(project_root, YCONFIG_FILE)
    parser = make_parser(
        project_config_file if os.path.isfile(project_config_file) else None)
    argcomplete.autocomplete(parser)
    return Config(parser.parse(argv), project_root, work_dir)
