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


@pytest.mark.usefixtures('??')
def test_parser_error(basic_conf, capsys):
  #TODO(bergden) write test with some nice dag, where the failed branch won't run, and successful branch continues