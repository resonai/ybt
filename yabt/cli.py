# -*- coding: utf-8 -*-

# Copyright 2016 Resonai Ltd. All rights reserved
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

import json
from importlib.machinery import SourceFileLoader
import os

import argcomplete
import colorama
import configargparse

from ostrich.utils.collections import listify

from .config import BUILD_PROJ_FILE, Config, YCONFIG_FILE, YSETTINGS_FILE
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
        PARSER.add('--artifacts-metadata-file',
                   help='Output file to write artifacts metadata to')
        PARSER.add('--continue-after-fail', default=False, action='store_true',
                   help='If a target fails continue independent targets')
        PARSER.add('--bin-output-dir', default='ybt_bin')
        PARSER.add('--build-file-name', default='YBuild')
        PARSER.add('--build-base-images', action='store_true')
        PARSER.add('--builders-workspace-dir', default='yabtwork')
        PARSER.add('--default-target-name', default='@default')
        PARSER.add('--docker-pull-cmd', default='docker pull',
                   help='Command to use for pulling images from registries')
        PARSER.add('--docker-push-cmd', default='docker push',
                   help='Command to use for pushing images to registries')
        PARSER.add('--docker-volume',
                   help='Use the specified docker volume as buildenv /project')
        PARSER.add('-f', '--flavor', help='Choose build flavor (AKA profile)')
        PARSER.add('--force-pull', action='store_true')
        PARSER.add('-j', '--jobs', type=int, default=1)
        # TODO(itamar): support auto-detection of interactivity-mode
        PARSER.add('--non-interactive', action='store_true')
        PARSER.add('--offline', action='store_true')
        PARSER.add('--output-dot-file', default=None,
                   help='Output file for dot graph (default: stdin)')
        # TODO(itamar): this flag should come from the builder, not from here
        PARSER.add('--push', action='store_true')
        PARSER.add('--runtime-params', type=json.loads,
                   help='Params to pass to the docker run command in json')
        PARSER.add('--scm-provider')
        PARSER.add('--no-build-cache', action='store_true',
                   help='Disable YBT build cache')
        PARSER.add('--no-docker-cache', action='store_true',
                   help='Disable YBT Docker cache')
        PARSER.add('--no-policies', action='store_true')
        PARSER.add('--no-test-cache', action='store_true',
                   help='Disable YBT test cache')
        PARSER.add('--test-attempts', type=int, default=1)
        PARSER.add('-v', '--verbose', action='store_true',
                   help='More verbose output to STDOUT')
        PARSER.add('--with-tini-entrypoint', action='store_true')
        # Logging flags
        PARSER.add('--logtostderr', action='store_true',
                   help='Whether to log to STDERR')
        PARSER.add('--logtostdout', action='store_true',
                   help='Whether to log to STDOUT')
        PARSER.add('--loglevel', default='INFO', choices=LOG_LEVELS_CHOICES,
                   help='Log level threshold')
        PARSER.add('--show-buildenv-deps', type=bool, default=False,
                   help='When running dot, if set to True then the buildenv '
                        'targets are printed to the graph too')
        PARSER.add('--download-from-global-cache', default=False,
                   action='store_true',
                   help='download from global cache targets that are not '
                        'cached locally')
        PARSER.add('--upload-to-global-cache', default=False,
                   action='store_true',
                   help='upload to global cache targets that were built')
        PARSER.add('--download-tests-from-global-cache', default=False,
                   action='store_true',
                   help='download from global cache tests that are not '
                        'cached locally')
        PARSER.add('--upload-tests-to-global-cache', default=False,
                   action='store_true',
                   help='upload to global cache tests that were run')
        PARSER.add('cmd', choices=['build', 'dot', 'test', 'tree', 'version'])
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


def get_user_settings_module(project_root: str):
    """Return project-specific user settings module, if it exists.

    :param project_root: Absolute path to project root directory.

    A project settings file is a file named `YSETTINGS_FILE` found at the top
    level of the project root dir.

    Return `None` if project root dir is not specified,
    or if no such file is found.

    Raise an exception if a file is found, but not importable.

    The YSettings file can define 2 special module-level functions that
    interact with the YABT CLI & config system:
    1. `extend_cli`, if defined, takes the YABT `parser` object and may extend
       it, to add custom command-line flags for the project.
       (careful not to collide with YABT flags...)
    2. `extend_config`, if defined, takes the YABT `config` object and the
       parsed `args` object (returned by the the parser), and may extend the
       config - should be used to reflect custom project CLI flags in the
       config object.

    Beyond that, the settings module is available in YBuild's under
    `conf.settings` (except for the 2 special fucntions that are removed).
    """
    if project_root:
        project_settings_file = os.path.join(project_root, YSETTINGS_FILE)
        if os.path.isfile(project_settings_file):
            settings_loader = SourceFileLoader(
                'settings', project_settings_file)
            return settings_loader.load_module()


def call_user_func(settings_module, func_name, *args, **kwargs):
    """Call a user-supplied settings function and clean it up afterwards.

    settings_module may be None, or the function may not exist.
    If the function exists, it is called with the specified *args and **kwargs,
    and the result is returned.
    """
    if settings_module:
        if hasattr(settings_module, func_name):
            func = getattr(settings_module, func_name)
            try:
                return func(*args, **kwargs)
            finally:
                # cleanup user function
                delattr(settings_module, func_name)


def get_build_flavor(settings_module, args):
    """Update the flavor arg based on the settings API"""
    known_flavors = listify(call_user_func(settings_module, 'known_flavors'))
    if args.flavor:
        if args.flavor not in known_flavors:
            raise ValueError('Unknown build flavor: {}'.format(args.flavor))
    else:
        args.flavor = call_user_func(settings_module, 'default_flavor')
        if args.flavor and args.flavor not in known_flavors:
            raise ValueError(
                'Unknown default build flavor: {}'.format(args.flavor))


def init_and_get_conf(argv: list=None) -> Config:
    """Initialize a YABT CLI environment and return a Config instance.

    :param argv: Manual override of command-line params to parse (for tests).
    """
    colorama.init()
    work_dir = os.path.abspath(os.curdir)
    project_root = search_for_parent_dir(work_dir,
                                         with_files=set([BUILD_PROJ_FILE]))
    parser = make_parser(find_project_config_file(project_root))
    settings_module = get_user_settings_module(project_root)
    call_user_func(settings_module, 'extend_cli', parser)
    argcomplete.autocomplete(parser)
    args = parser.parse(argv)
    get_build_flavor(settings_module, args)
    config = Config(args, project_root, work_dir, settings_module)
    config.common_conf = call_user_func(
        config.settings, 'get_common_config', config, args)
    config.flavor_conf = call_user_func(
        config.settings, 'get_flavored_config', config, args)
    call_user_func(config.settings, 'extend_config', config, args)
    if not args.no_policies:
        config.policies = listify(call_user_func(
            config.settings, 'get_policies', config))
    return config
