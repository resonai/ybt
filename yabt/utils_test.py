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
yabt utils tests
~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from os.path import join

import pytest

from .utils import hash_tree, hash_file


DATA_DIR = join('tests', 'data')


def test_hashing_files():
    hello_hash_tree = hash_tree(join(DATA_DIR, 'hello.txt'))
    world_hash_tree = hash_tree(join(DATA_DIR, 'world.txt'))
    hello_hash_file = hash_file(join(DATA_DIR, 'hello.txt'))
    world_hash_file = hash_file(join(DATA_DIR, 'world.txt'))
    assert hello_hash_tree == world_hash_tree
    assert hello_hash_tree == hello_hash_file
    assert world_hash_tree == world_hash_file
    assert hello_hash_tree == '910c8bc73110b0cd1bc5d2bcae782511'


def test_hashing_empty_file():
    empty_hash = hash_tree(join(DATA_DIR, 'empty'))
    assert empty_hash == 'd41d8cd98f00b204e9800998ecf8427e'


def test_hashing_dirs():
    # test data includes non-ASCII characters in content as well as file names
    top1_hash = hash_tree(join(DATA_DIR, 'top1'))
    top2_hash = hash_tree(join(DATA_DIR, 'top2'))
    top3_hash = hash_tree(join(DATA_DIR, 'top3'))
    # this also verifies that the dir hash is not dependent upon the absolute
    # path of the dir itself
    assert top1_hash == top2_hash
    # same files but different sub-dir name should result different hash
    assert top1_hash != top3_hash
    assert top1_hash == '22f04e1ed792828b7053542cf7ce0448'
    assert top3_hash == '6f510185466f003a25bc249921e39b4d'
