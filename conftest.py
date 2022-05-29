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
import shutil
import tempfile

import configargparse
import pytest
from pytest import fixture

import yabt
from yabt import cli


def pytest_addoption(parser):
    parser.addoption('--with-slow', action='store_true', help='run slow tests')


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--with-slow"):
        return
    skip_slow = pytest.mark.skip(reason="need --with-slow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


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


@fixture
def in_simple_project():
    yield from yabt_project_fixture('simple')

@fixture
def in_simpleflat_project():
    yield from yabt_project_fixture('simpleflat')

@fixture
def in_dag_project():
    yield from yabt_project_fixture('dag')


@fixture
def in_error_project():
    yield from yabt_project_fixture('errors')


@fixture
def in_yapi_dir():
    yield from yabt_project_fixture(os.path.join('dag', 'yapi'))


@fixture
def in_pkgmgrs_project():
    yield from yabt_project_fixture('pkgmgrs')


@fixture
def in_proto_project():
    yield from yabt_project_fixture('proto')


@fixture
def in_caching_project():
    yield from yabt_project_fixture('caching')


@fixture
def in_cpp_project():
    yield from yabt_project_fixture('cpp')


@fixture
def in_tests_project():
    yield from yabt_project_fixture('tests')


@fixture
def in_custom_installer_project():
    yield from yabt_project_fixture('custom_installer')


@fixture
def in_golang_project():
    yield from yabt_project_fixture('golang')


@fixture
def tmp_dir():
    orig_dir = os.getcwd()
    _tmp_dir = tempfile.mkdtemp()
    os.chdir(_tmp_dir)
    yield _tmp_dir
    os.chdir(orig_dir)
    shutil.rmtree(_tmp_dir)


@fixture
def basic_conf():
    reset_parser()
    conf = cli.init_and_get_conf([
        '--non-interactive', '--no-build-cache', '--no-test-cache',
        '--no-docker-cache', 'build'])
    yabt.extend.Plugin.load_plugins(conf)
    yield conf


@fixture()
def debug_conf():
    reset_parser()
    conf = cli.init_and_get_conf([
        '--non-interactive', '-f', 'debug', '--no-build-cache',
        '--no-test-cache', '--no-docker-cache', 'build'])
    yabt.extend.Plugin.load_plugins(conf)
    yield conf


@fixture
def nopolicy_conf():
    reset_parser()
    conf = cli.init_and_get_conf([
        '--non-interactive', '--no-build-cache', '--no-test-cache',
        '--no-docker-cache','--no-policies', 'build'])
    yabt.extend.Plugin.load_plugins(conf)
    yield conf
