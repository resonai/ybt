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
yabt py.test conftest
~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import os

import configargparse
import pytest
from pytest import yield_fixture

import yabt
from yabt import cli


def pytest_addoption(parser):
    parser.addoption('--with-slow', action='store_true', help='run slow tests')


def reset_parser():
    """Disgusting hack to work around configargparse singleton pattern that
       creates cross-test contamination.
    """
    cli.PARSER = None
    configargparse._parsers = {}


def yabt_project_fixture(project):
    orig_dir = os.getcwd()
    tests_work_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'tests', project))
    os.chdir(tests_work_dir)
    yield
    os.chdir(orig_dir)


@yield_fixture
def in_simple_project():
    yield from yabt_project_fixture('simple')


@yield_fixture
def in_dag_project():
    yield from yabt_project_fixture('dag')


@yield_fixture
def in_error_project():
    yield from yabt_project_fixture('errors')


@yield_fixture
def in_yapi_dir():
    yield from yabt_project_fixture(os.path.join('dag', 'yapi'))


@yield_fixture
def in_pkgmgrs_project():
    yield from yabt_project_fixture('pkgmgrs')


@yield_fixture
def in_proto_project():
    yield from yabt_project_fixture('proto')


@yield_fixture
def in_caching_project():
    yield from yabt_project_fixture('caching')


@yield_fixture
def in_cpp_project():
    yield from yabt_project_fixture('cpp')


@yield_fixture
def in_tests_project():
    yield from yabt_project_fixture('tests')


@yield_fixture
def basic_conf():
    reset_parser()
    conf = cli.init_and_get_conf(['--non-interactive', 'build'])
    yabt.extend.Plugin.load_plugins(conf)
    yield conf


@yield_fixture()
def debug_conf():
    reset_parser()
    conf = cli.init_and_get_conf(['--non-interactive', '-f', 'debug', 'build'])
    yabt.extend.Plugin.load_plugins(conf)
    yield conf
