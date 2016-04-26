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
yabt Target utils tests
~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import pytest

from .target_utils import norm_name


def test_norm_name_abs_ref():
    """Test norm_name abs ref to targets in nested modules."""
    assert 'cat/foo:bar' == norm_name('cat', '//cat/foo:bar')
    assert 'cat:bar' == norm_name('cat', '//cat:bar')
    assert 'dog:bark' == norm_name('cat', '//dog:bark')
    assert 'stuff:*' == norm_name('cat', '//stuff:*')
    assert 'stuff/**:*' == norm_name('cat', '//stuff/**:*')


def test_norm_name_abs_ref_top_level():
    """Test norm_name abs ref to targets in top level module."""
    assert ':spam' == norm_name('cat', '//:spam')
    assert ':*' == norm_name('cat', '//:*')
    assert '**:*' == norm_name('cat', '//**:*')


def test_norm_name_rel_ref_sub():
    """Test norm_name rel ref to sub-module."""
    assert 'cat/foo:bar' == norm_name('cat', 'foo:bar')
    assert 'cat/foo:bar' == norm_name('cat', './foo:bar')
    assert 'cat/foo:*' == norm_name('cat', 'foo:*')
    assert 'cat/foo/**:*' == norm_name('cat', 'foo/**:*')


def test_norm_name_rel_ref_local():
    """Test norm_name rel ref to same module."""
    assert 'cat:bar' == norm_name('cat', ':bar')
    assert 'cat:bar' == norm_name('cat', '.:bar')
    assert 'cat:bar' == norm_name('cat', './:bar')
    assert 'cat:*' == norm_name('cat', ':*')
    assert 'cat/**:*' == norm_name('cat', '**:*')


def test_norm_name_rel_ref_sub():
    """Test norm_name rel ref to a sibling module."""
    assert 'dog:bark' == norm_name('cat', '../dog:bark')
    assert 'dog:bark' == norm_name('cat', '../dog/.:bark')
    assert 'dog:bark' == norm_name('cat', './../dog:bark')
    assert 'dog:bark' == norm_name('cat', '.././dog:bark')
    assert 'dog:*' == norm_name('cat', '../dog:*')
    assert 'dog/**:*' == norm_name('cat', '../dog/**:*')


def test_norm_name_escape_sandbox_error():
    """Test norm_name various sandbox-escaping scenarios."""
    for bad_name in [
            '///cat/foo:bar',
            '//../cat/foo:bar',
            '/etc/passwd:meow',
            '../..:paw']:
        with pytest.raises(ValueError) as excinfo:
            norm_name('cat', bad_name)
    assert 'must remain inside project sandbox' in str(excinfo.value)


def test_norm_name_unqualified_error():
    """Test norm_name when given unqualified target name."""
    with pytest.raises(ValueError) as excinfo:
        norm_name('cat', 'poops')
    assert ('Must provide fully-qualified target name (with `:\') to avoid '
            'possible ambiguity' in str(excinfo.value))
