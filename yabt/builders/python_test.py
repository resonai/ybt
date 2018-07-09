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


import pytest

from ..buildcontext import BuildContext
from ..graph import populate_targets_graph


slow = pytest.mark.skipif(not pytest.config.getoption('--with-slow'),
                          reason='need --with-slow option to run')


@slow
@pytest.mark.usefixtures('in_tests_project')
def test_python_tester_success(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['hello_pytest:greet-test']
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph(run_tests=True)


@slow
@pytest.mark.usefixtures('in_tests_project')
def test_python_tester_fail(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['hello_pytest:greet-failing-test']
    populate_targets_graph(build_context, basic_conf)
    with pytest.raises(SystemExit):
        build_context.build_graph(run_tests=True)
