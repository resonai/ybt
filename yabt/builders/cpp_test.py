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


from subprocess import check_output

import pytest

from . import cpp
from ..buildcontext import BuildContext
from ..graph import populate_targets_graph


slow = pytest.mark.skipif(not pytest.config.getoption('--with-slow'),
                          reason='need --with-slow option to run')


TEST_TARGETS = (
    'hello:hello-app', 'hello_lib:hello-app', 'hello_mod/main:hello-app')


@slow
@pytest.mark.parametrize('target_name', TEST_TARGETS)
@pytest.mark.usefixtures('in_cpp_project')
def test_cpp_builder(basic_conf, target_name):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = [target_name]
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph()
    hello_out = str(
        check_output(['ybt_bin/{}'.format(target_name.replace(':', '/'))]))
    assert 'Hello world' in hello_out
