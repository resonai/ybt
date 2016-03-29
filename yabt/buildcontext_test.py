# -*- coding: utf-8 -*-

"""
yabt Build context tests
~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2016 Yowza by Itamar Ostricher
:license: MIT, see LICENSE for more details.
"""


import pytest

from .buildcontext import BuildContext
from .builders.alias import AliasBuilder


@pytest.mark.usefixtures('in_simple_project')
def test_load_builders(basic_conf):
    builders = BuildContext.get_active_builders(basic_conf)
    assert len(builders) > 0
    assert AliasBuilder in builders
