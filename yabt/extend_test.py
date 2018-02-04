# -*- coding: utf-8 -*-

# Copyright 2016 Resonai Ltd. All rights reserved
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
yabt extension subsystem tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import pytest

from .extend import (
    Plugin, PropType as PT, register_builder_sig, register_build_func)


def test_load_plugins(basic_conf):
    # getting the `basic_conf` fixture makes sure that plugins are loaded
    assert len(Plugin.builders) > 0
    assert 'Alias' in Plugin.builders


def test_non_default_args_after_default_args_error():
    Plugin.remove_builder('Spam')
    with pytest.raises(SyntaxError) as excinfo:
        register_builder_sig('Spam', ['foo',
                                      ('cats', PT.TargetList, None),
                                      ('bar'),
                                      ])
    assert (
        'non-default argument follows default argument' in str(excinfo.value))


def test_dup_builder_sig_error():
    Plugin.remove_builder('Spam')
    register_builder_sig('Spam', [])
    with pytest.raises(KeyError) as excinfo:
        register_builder_sig('Spam', [])
    assert 'Spam already registered a signature!' in str(excinfo.value)


def test_dup_builder_func_error():
    Plugin.remove_builder('Spam')

    def spam_builder_1(build_context, target):
        pass

    register_build_func('Spam')(spam_builder_1)
    with pytest.raises(KeyError) as excinfo:
        register_build_func('Spam')(spam_builder_1)
    assert 'Spam already registered a build function!' in str(excinfo.value)


def test_register_build_sig_duplicate_arg():
    Plugin.remove_builder('Spam')
    with pytest.raises(SyntaxError) as excinfo:
        register_builder_sig('Spam', [('deps', PT.TargetList, None)])
    assert ("duplicate argument 'deps' in function definition"
            in str(excinfo.value))
    Plugin.remove_builder('Spam')
    with pytest.raises(SyntaxError) as excinfo:
        register_builder_sig('Spam', [('name', PT.TargetName)])
    assert ("duplicate argument 'name' in function definition"
            in str(excinfo.value))


def test_builder_sig_untyped_default_value():
    Plugin.remove_builder('Spam')
    register_builder_sig('Spam', [('foo', 'default foo')])
    assert PT.untyped == Plugin.builders['Spam'].sig['foo'].type
    assert 'default foo' == Plugin.builders['Spam'].sig['foo'].default
