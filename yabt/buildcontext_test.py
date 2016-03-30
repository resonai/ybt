# -*- coding: utf-8 -*-

# Copyright 2016 Yowza Ltd. All rights reserved
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
yabt Build context tests
~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import pytest

from .buildcontext import BuildContext
from .builders.alias import AliasBuilder


@pytest.mark.usefixtures('in_simple_project')
def test_load_builders(basic_conf):
    builders = BuildContext.get_active_builders(basic_conf)
    assert len(builders) > 0
    assert AliasBuilder in builders
