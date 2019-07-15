# -*- coding: utf-8 -*-

# Copyright 2018 Resonai Ltd. All rights reserved
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

:author: Itamar Ostricher
"""

import random
import pytest

from ..buildcontext import BuildContext
from ..graph import populate_targets_graph


@pytest.mark.slow
@pytest.mark.usefixtures('in_tests_project')
def test_python_tester_success(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['hello_pytest:greet-test']
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph(run_tests=True)


@pytest.mark.slow
@pytest.mark.usefixtures('in_tests_project')
def test_python_tester_fail(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['hello_pytest:greet-failing-test']
    populate_targets_graph(build_context, basic_conf)
    with pytest.raises(SystemExit):
        build_context.build_graph(run_tests=True)


@pytest.mark.slow
@pytest.mark.usefixtures('in_tests_project')
def test_python_tester_fail_no_exit(basic_conf, capsys):
    basic_conf.continue_after_fail = True
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['hello_pytest:greet-failing-test']
    populate_targets_graph(build_context, basic_conf)
    with pytest.raises(SystemExit):
        build_context.build_graph(run_tests=True)
    out, err = capsys.readouterr()
    err.encode()
    expected_error = "\x1b[31mFatal: Finished building target graph with \
fails: \n['hello_pytest:greet-failing-test']\nwhich caused the \
following to skip: \n[]\x1b[0m\n"
    expected_error.encode()
    assert err == expected_error


@pytest.mark.slow
@pytest.mark.usefixtures('in_tests_project')
def test_python_tester_fail_with_retry(basic_conf):
    build_context = BuildContext(basic_conf)
    target_name = 'hello_pytest:greet-failing-test'
    basic_conf.targets = [target_name]
    populate_targets_graph(build_context, basic_conf)
    target = build_context.targets[target_name]
    target.props.attempts = 5
    with pytest.raises(SystemExit):
        build_context.build_graph(run_tests=True)
    assert target.info['fail_count'] == 5


@pytest.mark.slow
@pytest.mark.usefixtures('in_tests_project')
def test_python_tester_flaky(basic_conf):
    build_context = BuildContext(basic_conf)
    target_name = 'hello_pytest:flaky-test'
    basic_conf.targets = [target_name]
    populate_targets_graph(build_context, basic_conf)
    target = build_context.targets[target_name]
    target.props.test_env['RANDOM_FILE'] = str(random.randint(0, 20000))
    build_context.build_graph(run_tests=True)
    assert target.info['fail_count'] == 1


@pytest.mark.slow
@pytest.mark.usefixtures('in_tests_project')
def test_python_tester_aba(basic_conf):
    build_context = BuildContext(basic_conf)
    target_a_name = 'hello_pytest:test-a'
    target_b_name = 'hello_pytest:test-b'
    basic_conf.targets = [target_a_name, target_b_name]
    populate_targets_graph(build_context, basic_conf)
    target_a = build_context.targets[target_a_name]
    target_b = build_context.targets[target_b_name]
    random_file = str(random.randint(0, 20000))
    target_a.props.test_env['RANDOM_FILE'] = random_file
    target_b.props.test_env['RANDOM_FILE'] = random_file
    build_context.build_graph(run_tests=True)
    assert (
        target_a.info['fail_count'] == 1 or target_b.info['fail_count'] == 1)
    assert (
        target_a.info['fail_count'] == 0 or target_b.info['fail_count'] == 0)
