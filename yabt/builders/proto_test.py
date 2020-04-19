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

:author: Zohar Rimon
"""


import os
from os.path import isdir, isfile, join
import shutil
from subprocess import PIPE

import pytest

from conftest import reset_parser
from .. import cli, extend
from . import proto
from ..buildcontext import BuildContext
from ..graph import populate_targets_graph
from ..utils import yprint


def clear_output():
    try:
        shutil.rmtree('build')
    except FileNotFoundError:
        pass


@pytest.mark.slow
@pytest.mark.usefixtures('in_proto_project')
def test_proto_builder(basic_conf):
    clear_output()
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['app:hello-proto']
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph()
    assert isdir('build')
    assert isdir(join('build', 'gen'))
    assert isdir(join('build', 'gen', 'proto'))
    assert isfile(join('build', 'gen', 'proto', '__init__.py'))
    assert isdir(join('build', 'gen', 'proto', 'app'))
    assert isfile(join('build', 'gen', 'proto', 'app', '__init__.py'))
    for exp_gen_fname in [
        'hello.pb.cc',
        'hello.pb.h',
        'hello_pb2.py'
    ]:
        assert isfile(join('build', 'gen', 'proto', 'app', exp_gen_fname))
    clear_output()


@pytest.mark.slow
@pytest.mark.usefixtures('in_proto_project')
def test_proto_cpp_prog(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['app:hello-prog']
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph()
    work_dir = build_context.conf.host_to_buildenv_path(
        build_context.get_workspace('CppProg', 'app:hello-prog'))
    result = build_context.run_in_buildenv(
        ':proto-builder', [join(work_dir, 'app', 'hello-prog')],
        stdout=PIPE, stderr=PIPE)
    assert 0 == result.returncode
    assert b'Hello, World!' == result.stdout


@pytest.mark.slow
@pytest.mark.usefixtures('in_proto_project')
def test_proto_collector(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['app:hello1-collector']
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph()
    assert_all_proto_files_exist()


@pytest.mark.slow
@pytest.mark.usefixtures('in_proto_project')
def test_proto_collector_build_from_cache():
    # Create cache
    reset_parser()
    conf = cli.init_and_get_conf(['--non-interactive', 'build'])
    extend.Plugin.load_plugins(conf)
    build_context = BuildContext(conf)
    conf.targets = ['app:hello1-collector']
    populate_targets_graph(build_context, conf)
    build_context.build_graph()

    # Build from cache
    shutil.rmtree(join('yabtwork', 'flavor__all__'))
    build_context2 = BuildContext(conf)
    populate_targets_graph(build_context2, conf)
    build_context2.build_graph()
    assert_all_proto_files_exist()


def assert_all_proto_files_exist():
    assert isdir('yabtwork')
    assert isdir(join('yabtwork', 'flavor__all__'))
    assert isdir(join('yabtwork', 'flavor__all__', 'ProtoCollector'))
    assert isdir(join('yabtwork', 'flavor__all__', 'ProtoCollector',
                      'app_hello1-collector'))
    assert isdir(join('yabtwork', 'flavor__all__', 'ProtoCollector',
                      'app_hello1-collector', 'proto'))
    assert isdir(join('yabtwork', 'flavor__all__', 'ProtoCollector',
                      'app_hello1-collector', 'proto', 'app'))
    assert isdir(join('yabtwork', 'flavor__all__', 'ProtoCollector',
                      'app_hello1-collector', 'proto', 'app', 'hello1'))
    assert isfile(join('yabtwork', 'flavor__all__', 'ProtoCollector',
                       'app_hello1-collector', 'proto', 'app', 'hello1',
                       'hello1.proto'))
    assert isdir(join('yabtwork', 'flavor__all__', 'ProtoCollector',
                      'app_hello1-collector', 'proto', 'app', 'hello2'))
    assert isfile(join('yabtwork', 'flavor__all__', 'ProtoCollector',
                       'app_hello1-collector', 'proto', 'app', 'hello2',
                       'hello2.proto'))
