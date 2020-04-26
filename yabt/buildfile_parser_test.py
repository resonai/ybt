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
yabt buildfile parser tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""

from os.path import join
import re

import pytest

from .buildcontext import BuildContext
from .graph import populate_targets_graph
from .logging import make_logger
logger = make_logger(__name__)


@pytest.mark.usefixtures('in_error_project')
def test_parser_error(basic_conf, capsys):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['parser-error']
    with pytest.raises(SystemExit):
        populate_targets_graph(build_context, basic_conf)
    _, err = capsys.readouterr()
    ybuild_path = re.escape(join('tests', 'errors', 'parser-error', 'YBuild'))
    logger.debug('test_parser_error: {}', err)
    assert re.search('{}\",\\ line\\ [4-8]'.format(ybuild_path), err)
    assert (
        "Fatal: Must provide fully-qualified target name (with `:') to "
        "avoid possible ambiguity - `users' not valid\n" in err)
