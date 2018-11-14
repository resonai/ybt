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
yabt buildcontext tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Shai Ghelberg
"""

from os.path import join

import pytest

from .buildcontext import BuildContext
from .graph import populate_targets_graph

slow = pytest.mark.skipif(not pytest.config.getoption('--with-slow'),
                          reason='need --with-slow option to run')


@slow
@pytest.mark.usefixtures('in_tests_project')
def test_continue_after_fail(basic_conf):
    '''
    Testing this thing:
    We want to have targets A, B, C and D where B and D are tests that depand
    on A and C respectively.
    A is a faulty build that will cause C to be skipped.
    D will pass after B is built.
    To test that we "continued after fail" we need to make sure
    A runs and fails before we reach B.
    This is what we want:
    A -X-> C (skipped)
    B --> D
    Such test is icky, because we can't promise anything about the order in
    which indepedant branches run.
    If BD would run before AC we can't distinguish that behavior from AC
    failing and BD running thanks to the flag.
    Sope, we generate 10 AC-alikes and 10 BD-alikes, and statistically assume
    at least one BD pair would run after an AD pair.
    Finally we assert, A failed, C skipped, and BD ran successfuly (10 times).
    '''

    # TODO(bergden) do it what he said.....
