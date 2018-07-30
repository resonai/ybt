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
yabt Target utils tests
~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""

from os.path import join

import pytest

from .buildcontext import BuildContext
from .graph import populate_targets_graph
from .target_utils import hashify_files, hashify_targets, norm_name


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


_EXP_JSON = """{
    "buildenv": [],
    "builder_name": "CppApp",
    "deps": [
        "9622d221dd088a77b148ceec6a9f6aee",
        "c6bf2ffb8837d4a66b4efbd7ec642bac"
    ],
    "flavor": null,
    "name": "app:hello-prog-app",
    "props": {
        "base_image": [
            "9622d221dd088a77b148ceec6a9f6aee"
        ],
        "build_params": {},
        "build_user": null,
        "distro": {},
        "docker_labels": {},
        "env": {},
        "executable": {},
        "full_path_cmd": false,
        "image_name": null,
        "image_tag": "latest",
        "main": [
            "c6bf2ffb8837d4a66b4efbd7ec642bac"
        ],
        "packaging_params": {},
        "run_user": null,
        "runtime_params": {},
        "work_dir": "/usr/src/app"
    },
    "tags": []
}"""


@pytest.mark.usefixtures('in_proto_project')
def test_target_hash_and_json(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['app:hello-prog-app']
    populate_targets_graph(build_context, basic_conf)
    assert ('c6bf2ffb8837d4a66b4efbd7ec642bac' ==
            build_context.targets['app:hello-prog'].hash(build_context))
    assert ('9622d221dd088a77b148ceec6a9f6aee' ==
            build_context.targets[':proto-builder'].hash(build_context))
    prog_app = build_context.targets['app:hello-prog-app']
    prog_app.compute_json(build_context)
    assert _EXP_JSON == prog_app.json(build_context)


@pytest.mark.usefixtures('in_proto_project')
def test_hashify_targets(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['app:hello-prog-app']
    populate_targets_graph(build_context, basic_conf)
    assert [
        '9622d221dd088a77b148ceec6a9f6aee',
        'c6bf2ffb8837d4a66b4efbd7ec642bac',
    ] == hashify_targets(['app:hello-prog', ':proto-builder'], build_context)


def test_hashify_files():
    files = [join(join('tests', 'data'), fname)
             for fname in ('empty', 'hello.txt', 'world.txt')]
    hashed_files = hashify_files(files)
    assert {
        'tests/data/empty': 'd41d8cd98f00b204e9800998ecf8427e',
        'tests/data/hello.txt': '910c8bc73110b0cd1bc5d2bcae782511',
        'tests/data/world.txt': '910c8bc73110b0cd1bc5d2bcae782511',
    } == hashed_files
