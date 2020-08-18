# -*- coding: utf-8 -*-

# Copyright 2020 Resonai Ltd. All rights reserved
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
yabt Go Builder Tests

:author: Itamar Ostricher
"""


from subprocess import check_output

import pytest

from ..buildcontext import BuildContext
from ..graph import populate_targets_graph


@pytest.mark.slow
@pytest.mark.usefixtures('in_golang_project')
def test_golang_builder(basic_conf):
    build_context = BuildContext(basic_conf)
    target_name = 'hello:hello-app'
    basic_conf.targets = [target_name]
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph(run_tests=True)
    hello_out = check_output(
        ['docker', 'run', '--rm', build_context.targets[target_name].image_id,
         '-who', 'app'])
    expected = br"""
  _              _   _
 | |__     ___  | | | |   ___       __ _   _ __    _ __
 | '_ \   / _ \ | | | |  / _ \     / _` | | '_ \  | '_ \
 | | | | |  __/ | | | | | (_) |   | (_| | | |_) | | |_) |
 |_| |_|  \___| |_| |_|  \___/     \__,_| | .__/  | .__/
                                          |_|     |_|
"""
    assert expected == (b'\n' + hello_out)


@pytest.mark.slow
@pytest.mark.usefixtures('in_golang_project')
def test_golang_test(basic_conf):
    build_context = BuildContext(basic_conf)
    target_name = 'hello_lib:utils_test'
    basic_conf.targets = [target_name]
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph(run_tests=True)


@pytest.mark.slow
@pytest.mark.usefixtures('in_golang_project')
def test_golang_test_multisrc(basic_conf):
    build_context = BuildContext(basic_conf)
    target_name = 'goodbye_lib:goodbye_utils_test'
    basic_conf.targets = [target_name]
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph(run_tests=True)


@pytest.mark.slow
@pytest.mark.usefixtures('in_golang_project')
def test_golang_test_mainfuncs(basic_conf):
    build_context = BuildContext(basic_conf)
    target_name = 'goodbye:goodbye-test'
    basic_conf.targets = [target_name]
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph(run_tests=True)


@pytest.mark.slow
@pytest.mark.usefixtures('in_proto_project')
def test_golang_builder_proto(basic_conf):
    build_context = BuildContext(basic_conf)
    target_name = 'app:hello-go-app'
    basic_conf.targets = [target_name]
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph(run_tests=True)
    hello_out = check_output(
        ['docker', 'run', '--rm', build_context.targets[target_name].image_id,
         '-who', 'boomer'])
    assert hello_out == b'message: "hello boomer"\n\n'
