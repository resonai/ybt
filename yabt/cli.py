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
from .utils import search_for_parent_dir


PARSER = None
KNOWN_LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
LOG_LEVELS_CHOICES = KNOWN_LOG_LEVELS + [level.lower()
                                         for level in KNOWN_LOG_LEVELS]


def make_parser(project_config_file: str) -> configargparse.ArgumentParser:
    """Return the argument parser.

    :param project_config_file: Absolute path to project-specific config file.

    If cached parser already exists - return it immediately.
    Otherwise, initialize a new `ConfigArgParser` that is able to take default
    values from a hierarchy of config files and environment variables, as well
    as standard ArgParse command-line parsing behavior.

    We take default values from configuration files:

    - System-wide (see code for location)
    - User-level overrides (see code for location, hopefully under home dir)
    - If a project-specific config file is available, it will override both
      of the above.

    Environment variables will override all configuration files.
    For an option `--foo-bar`, if an environment variable named `YBT_FOO_VAR`
    exists, the option value will be taken from there.

    Of course, options specified directly on the command-line always win.
    """
    global PARSER  # pylint: disable=global-statement
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
        PARSER.add('--build-file-name', default='YBuild')
        PARSER.add('--build-base-images', action='store_true')
        PARSER.add('--builders-workspace-dir', default='yabtwork')
        PARSER.add('--default-target-name', default='@default')
        PARSER.add('--force-pull', action='store_true')
        PARSER.add('--offline', action='store_true')
        # TODO(itamar): this flag should come from the builder, not from here
        PARSER.add('--push', action='store_true')
        PARSER.add('--scm-provider')
        # Logging flags
        PARSER.add('--logtostderr', action='store_true',
                   help='Whether to log to STDERR')
        PARSER.add('--logtostdout', action='store_true',
                   help='Whether to log to STDOUT')
        PARSER.add('--loglevel', default='INFO', choices=LOG_LEVELS_CHOICES,
                   help='Log level threshold')
        PARSER.add('cmd',
                   choices=['build', 'tree', 'version', 'list-builders'],
                   nargs='?', default='build')
        PARSER.add('targets', nargs='*')
    return PARSER


def find_project_config_file(project_root: str) -> str:
    """Return absolute path to project-specific config file, if it exists.

    :param project_root: Absolute path to project root directory.

    A project config file is a file named `YCONFIG_FILE` found at the top
    level of the project root dir.

    Return `None` if project root dir is not specified,
    or if no such file is found.
    """
    if project_root:
        project_config_file = os.path.join(project_root, YCONFIG_FILE)
        if os.path.isfile(project_config_file):
            return project_config_file


def init_and_get_conf(argv: list=None) -> Config:
    """Initialize a YABT CLI environment and return a Config instance.

    :param argv: Manual override of command-line params to parse (for tests).
    """
    colorama.init()
    work_dir = os.path.abspath(os.curdir)
    project_root = search_for_parent_dir(work_dir,
                                         with_files=set([BUILD_PROJ_FILE]))
    parser = make_parser(find_project_config_file(project_root))
    argcomplete.autocomplete(parser)
    return Config(parser.parse(argv), project_root, work_dir)
