# -*- coding: utf-8 -*-

# Copyright 2019 Resonai Ltd. All rights reserved
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
dot generation tests
~~~~~~~~~~~~~~~~~~~~~~~

:author: Dana Shamir
"""


import io
import pytest
import re

from yabt.buildcontext import BuildContext
from yabt.dot import TARGETS_COLORS, write_dot, get_not_buildenv_targets
from yabt.graph import populate_targets_graph


slow = pytest.mark.skipif(not pytest.config.getoption('--with-slow'),
                          reason='need --with-slow option to run')


@pytest.mark.usefixtures('in_dag_project')
def test_graph_dot_generation(basic_conf):
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    expected_targets = {':flask', ':gunicorn', 'common:logging', 'common:base',
                        'fe:fe', 'yapi/server:users', 'yapi/server:yapi',
                        'yapi/server:yapi-gunicorn'}
    expected_dot_nodes = {'  "{}" [color="black",];'.format(target)
                          for target in expected_targets}
    expected_dot_edges = set([
        '  "common:base" -> "common:logging";',
        '  "fe:fe" -> "yapi/server:users";', '  "fe:fe" -> "common:base";',
        '  "fe:fe" -> ":flask";', '  "yapi/server:yapi" -> "common:base";',
        '  "yapi/server:yapi" -> ":flask";',
        '  "yapi/server:yapi-gunicorn" -> "yapi/server:yapi";',
        '  "yapi/server:yapi-gunicorn" -> "common:base";',
        '  "yapi/server:yapi-gunicorn" -> ":gunicorn";'])
    with io.StringIO() as dot_io:
        write_dot(build_context, basic_conf, dot_io)
        dot_lines = dot_io.getvalue().strip('\n').split('\n')
        assert 'strict digraph  {' == dot_lines[0]
        assert '}' == dot_lines[-1]
        assert expected_dot_nodes == set(dot_lines[1:9])
        assert expected_dot_edges == set(dot_lines[9:18])


@pytest.mark.usefixtures('in_simpleflat_project')
def test_graph_dot_generation_colors(basic_conf):
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    expected_targets = {':flask-0.10.1': TARGETS_COLORS['PythonPackage'],
                        ':flask-hello-app': TARGETS_COLORS['Python']}
    expected_dot_nodes = ['  "{}" [color="{}",];'.format(target, color)
                          for target, color in expected_targets.items()]
    with io.StringIO() as dot_io:
        write_dot(build_context, basic_conf, dot_io)
        dot_lines = dot_io.getvalue().strip('\n').split('\n')
        for dot_node in expected_dot_nodes:
            assert dot_node in dot_lines


@pytest.mark.usefixtures('in_cpp_project')
def test_no_buildenv_deps_in_dot(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['hello:hello-app']
    populate_targets_graph(build_context, basic_conf)
    buildenv_targets = {':builder', ':ubuntu-gpg', ':clang', ':gnupg'}
    expected_targets = {'hello:hello-app', 'hello:hello', ':ubuntu'}
    with io.StringIO() as dot_io:
        write_dot(build_context, basic_conf, dot_io)
        all_targets = set(dot_io.getvalue().split('"'))
        assert not buildenv_targets.intersection(all_targets)
        assert expected_targets.intersection(all_targets) == expected_targets


@slow
@pytest.mark.usefixtures('in_caching_project')
def test_cached_targets_different_color(basic_conf):
    basic_conf.targets = [':builder']
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    cached_targets = {':build-tools', ':tools', ':unzip', ':ubuntu'}
    other_targets = {':builder', ':builder-base'}
    expected_dot_nodes = set([
        '  "{}" \[color=".*",fillcolor="grey",style=filled\];'.format(target)
        for target in cached_targets] + [
        '  "{}" \[color=".*",\];'.format(target) for target in other_targets])
    with io.StringIO() as dot_io:
        write_dot(build_context, basic_conf, dot_io)
        dot_lines = dot_io.getvalue().strip('\n').split('\n')
        assert set(filter(lambda expected:
                          any(filter(lambda line: re.match(expected, line),
                                     dot_lines[1:7])),
                          expected_dot_nodes)) == expected_dot_nodes


@pytest.mark.usefixtures('in_cpp_project')
def test_buildenv_and_target_dep(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['hello_lib:hello-gnupg']
    populate_targets_graph(build_context, basic_conf)
    assert ':gnupg' in get_not_buildenv_targets(build_context)
