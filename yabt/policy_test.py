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
yabt policies tests
~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""

import pytest

from .buildcontext import BuildContext
from .graph import populate_targets_graph


@pytest.mark.usefixtures('in_error_project')
def test_policy_violation_unknown_license_name(basic_conf):
    basic_conf.targets = ['policy:bad-license-name']
    build_context = BuildContext(basic_conf)
    with pytest.raises(RuntimeError) as excinfo:
        populate_targets_graph(build_context, basic_conf)
    err_str = str(excinfo.value)
    assert ('Target policy:bad-license-name violates standard_licenses_only '
            'policy: Unknown license: GPLv3' in err_str)
    # asserting for 1 policy violation
    assert 2 == len(err_str.split('\n'))


@pytest.mark.usefixtures('in_error_project')
def test_policy_violation_bad_prod_license(basic_conf):
    basic_conf.targets = ['policy:app']
    build_context = BuildContext(basic_conf)
    with pytest.raises(RuntimeError) as excinfo:
        populate_targets_graph(build_context, basic_conf)
    err_str = str(excinfo.value)
    assert ('Target policy:app violates whitelist_prod_licenses policy: '
            'Invalid licenses for prod policy: GPL-3.0' in err_str)
    # asserting for 1 policy violation
    assert 2 == len(err_str.split('\n'))


@pytest.mark.usefixtures('in_error_project')
def test_no_violation(basic_conf):
    basic_conf.targets = ['policy:test']
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    # asserting no exception thrown


@pytest.mark.usefixtures('in_error_project')
def test_multiple_policy_violations(basic_conf):
    basic_conf.targets = ['policy']
    build_context = BuildContext(basic_conf)
    with pytest.raises(RuntimeError) as excinfo:
        populate_targets_graph(build_context, basic_conf)
    err_str = str(excinfo.value)
    assert ('Target policy:bad-license-name violates standard_licenses_only '
            'policy: Unknown license: GPLv3' in err_str)
    assert ('Target policy:app violates whitelist_prod_licenses policy: '
            'Invalid licenses for prod policy: GPL-3.0' in err_str)
    # asserting for 2 policy violations
    assert 3 == len(err_str.split('\n'))


@pytest.mark.usefixtures('in_error_project')
def test_disable_policy(nopolicy_conf):
    nopolicy_conf.targets = ['policy']
    build_context = BuildContext(nopolicy_conf)
    populate_targets_graph(build_context, nopolicy_conf)
    # asserting no exception thrown
