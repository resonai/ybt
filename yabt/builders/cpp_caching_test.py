# -*- coding: utf-8 -*-

# Copyright 2021 Resonai Ltd. All rights reserved
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
cpp caching tests
~~~~~~~~~~~~~~~~~~

:author: Dana Shamir
"""

from os import path
import os
from subprocess import check_output

import pytest
import shutil

from .. import cli
from ..buildcontext import BuildContext
from ..graph import populate_targets_graph

PROJECT_DIR = path.join(path.dirname(path.abspath(__file__)), '..', '..',
                        'tests', 'cpp_caching')
OP_OBJ_FILE = path.join('yabtwork', 'release_flavor', 'CppLib',
                        '_binary_operation', 'src', 'binary_operation.o')


def build_main_app():
    basic_conf = cli.init_and_get_conf(
        ['--non-interactive', '--continue-after-fail', 'build'])
    build_context = BuildContext(basic_conf)
    basic_conf.targets = [':main-app']
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph()


def build_test():
    basic_conf = cli.init_and_get_conf(
        ['--non-interactive', '--continue-after-fail', 'build'])
    build_context = BuildContext(basic_conf)
    basic_conf.targets = [':op_user_test']
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph(run_tests=True)


@pytest.mark.slow
@pytest.mark.skip(reason="Not supported feature")
def test_caching_prog(tmp_dir):
    shutil.copytree(PROJECT_DIR, 'cpp_caching')
    os.chdir('cpp_caching')

    build_main_app()
    op_obj_timestamp = path.getmtime(OP_OBJ_FILE)
    assert check_output(['docker', 'run', 'main-app:latest']) == b'12'

    with open('binary_operation.cc', 'r') as f:
        binary_operation_code = f.read()
    with open('binary_operation.cc', 'w') as f:
        f.write(binary_operation_code.replace('+', '*'))

    build_main_app()
    assert op_obj_timestamp == path.getmtime(OP_OBJ_FILE)  # This assert fails
    assert check_output(['docker', 'run', 'main-app:latest']) == b'20'


@pytest.mark.slow
@pytest.mark.skip(reason="Not supported feature")
def test_caching_gtest(tmp_dir):
    shutil.copytree(PROJECT_DIR, 'cpp_caching')
    os.chdir('cpp_caching')

    build_test()
    op_obj_timestamp = path.getmtime(OP_OBJ_FILE)

    with open('binary_operation.cc', 'r') as f:
        binary_operation_code = f.read()
    with open('binary_operation.cc', 'w') as f:
        f.write(binary_operation_code.replace('+', '*'))

    with pytest.raises(SystemExit):
        build_test()
    assert op_obj_timestamp == path.getmtime(OP_OBJ_FILE)  # This assert fails
