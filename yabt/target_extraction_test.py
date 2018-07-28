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
yabt Target extraction tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from os import path

import pytest

from .buildcontext import BuildContext
from .extend import (
    Plugin, PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from .target_extraction import args_to_props, extractor, handle_typed_args
from .target_utils import Target


@pytest.yield_fixture
def with_spam_builder_sig():
    Plugin.remove_builder('Spam')
    register_builder_sig('Spam', ['foo',
                                  ('bar', PT.str),
                                  ('cats', PT.StrList, None),
                                  ('cat_list', PT.File, None),
                                  ])
    yield


@pytest.mark.usefixtures('with_spam_builder_sig')
def test_build_sig_args_to_props_valid_positional_args():
    target = Target(builder_name='Spam')
    args_to_props(target, Plugin.builders['Spam'],
                  args=['my-spam', 'foo', 'bar'], kwargs={})
    assert target.props == {'name': 'my-spam', 'foo': 'foo', 'bar': 'bar',
                            'deps': None, 'cachable': True,
                            'cats': None, 'cat_list': None,
                            'packaging_params': None,
                            'runtime_params': None,
                            'build_params': None}


@pytest.mark.usefixtures('with_spam_builder_sig')
def test_build_sig_args_to_props_missing_one_pos_arg():
    target = Target(builder_name='Spam')
    with pytest.raises(TypeError) as excinfo:
        args_to_props(target, Plugin.builders['Spam'],
                      args=['my-spam', 'foo'], kwargs={})
    assert ("Spam() missing 1 required positional argument: 'bar'"
            in str(excinfo.value))


@pytest.mark.usefixtures('with_spam_builder_sig')
def test_build_sig_args_to_props_missing_two_pos_args():
    target = Target(builder_name='Spam')
    with pytest.raises(TypeError) as excinfo:
        args_to_props(target, Plugin.builders['Spam'],
                      args=['my-spam'], kwargs={})
    assert ("Spam() missing 2 required positional arguments: 'foo', 'bar'"
            in str(excinfo.value))


@pytest.mark.usefixtures('with_spam_builder_sig')
def test_build_sig_args_to_props_missing_all_pos_args():
    target = Target(builder_name='Spam')
    with pytest.raises(TypeError) as excinfo:
        args_to_props(target, Plugin.builders['Spam'],
                      args=[], kwargs={})
    assert ("Spam() missing 3 required positional arguments: "
            "'name', 'foo', 'bar'" in str(excinfo.value))


@pytest.mark.usefixtures('with_spam_builder_sig')
def test_build_sig_args_to_props_valid_mix_pos_kwargs():
    target = Target(builder_name='Spam')
    args_to_props(target, Plugin.builders['Spam'],
                  args=['my-spam'], kwargs={'foo': 'foo', 'bar': 'bar'})
    assert target.props == {'name': 'my-spam', 'foo': 'foo', 'bar': 'bar',
                            'deps': None, 'cachable': True,
                            'cats': None, 'cat_list': None,
                            'packaging_params': None,
                            'runtime_params': None,
                            'build_params': None}


@pytest.mark.usefixtures('with_spam_builder_sig')
def test_build_sig_args_to_props_mix_pos_kwargs_missing_pos_arg():
    target = Target(builder_name='Spam')
    with pytest.raises(TypeError) as excinfo:
        args_to_props(target, Plugin.builders['Spam'],
                      args=['my-spam'], kwargs={'bar': 'bar'})
    assert ("Spam() missing 1 required positional argument: 'foo'"
            in str(excinfo.value))


@pytest.mark.usefixtures('with_spam_builder_sig')
def test_build_sig_args_to_props_mix_pos_kwargs_dup_arg():
    target = Target(builder_name='Spam')
    with pytest.raises(TypeError) as excinfo:
        args_to_props(target, Plugin.builders['Spam'],
                      args=['my-spam'], kwargs={'name': 'my-spam'})
    assert ("Spam() got multiple values for argument 'name'"
            in str(excinfo.value))


@pytest.mark.usefixtures('with_spam_builder_sig')
def test_build_sig_args_to_props_mix_pos_kwargs_unexpected_kwarg():
    target = Target(builder_name='Spam')
    with pytest.raises(TypeError) as excinfo:
        args_to_props(target, Plugin.builders['Spam'],
                      args=['my-spam'], kwargs={'wtf': 'wait-for-it'})
    assert ("Spam() got an unexpected keyword argument 'wtf'"
            in str(excinfo.value))


@pytest.mark.usefixtures('with_spam_builder_sig')
def test_build_sig_args_to_props_too_many_pos_args():
    target = Target(builder_name='Spam')
    with pytest.raises(TypeError) as excinfo:
        args_to_props(target, Plugin.builders['Spam'],
                      args=['my-spam', 'foo', 'bar', None, None, None, None,
                            None, None, None, 'w00t'],
                      kwargs={})
    assert ('Spam() takes from 3 to 10 positional arguments, but 11 were given'
            in str(excinfo.value))


@pytest.mark.usefixtures('with_spam_builder_sig')
def test_target_extraction_bad_target_names(basic_conf):
    for bad_name in ['.', 'bad:name', ':', 'bad@name', '@', '**', 'foo/bar']:
        target = Target(builder_name='Spam')
        args_to_props(target, Plugin.builders['Spam'],
                      args=[bad_name, 'foo', 'bar'], kwargs={})
        with pytest.raises(ValueError) as excinfo:
            handle_typed_args(target, Plugin.builders['Spam'], 'spams')
        assert ("Invalid target name: `{}'".format(bad_name)
                in str(excinfo.value))


@pytest.mark.usefixtures('with_spam_builder_sig')
def test_typed_args_not_str():
    target = Target(builder_name='Spam')
    args_to_props(target, Plugin.builders['Spam'],
                  args=['my-spam', 'foo', 123], kwargs={})
    with pytest.raises(TypeError) as excinfo:
        handle_typed_args(target, Plugin.builders['Spam'], 'spams')
    assert 'bar: got `123`, expected string value' in str(excinfo.value)


@pytest.mark.usefixtures('with_spam_builder_sig')
def test_typed_args_valid_defaults():
    target = Target(builder_name='Spam')
    args_to_props(target, Plugin.builders['Spam'],
                  args=['my-spam', 'foo', 'bar'], kwargs={})
    handle_typed_args(target, Plugin.builders['Spam'], 'spams')
    assert target.props == {'name': 'spams:my-spam', 'foo': 'foo',
                            'bar': 'bar', 'deps': [], 'cachable': True,
                            'cats': [], 'cat_list': None,
                            'packaging_params': {},
                            'runtime_params': {},
                            'build_params': {}}


@pytest.mark.usefixtures('with_spam_builder_sig')
def test_typed_args_valid_non_default():
    target = Target(builder_name='Spam')
    args_to_props(target, Plugin.builders['Spam'],
                  args=['my-spam', 'foo', 'bar', ('my cat', 'other cat'),
                        '../lists/from-vet-4', '../hams:my-ham'],
                  kwargs={})
    handle_typed_args(target, Plugin.builders['Spam'], 'spams')
    assert target.props == {'name': 'spams:my-spam', 'foo': 'foo',
                            'bar': 'bar', 'deps': ['hams:my-ham'],
                            'cachable': True, 'cats': ['my cat', 'other cat'],
                            'cat_list': path.join('lists', 'from-vet-4'),
                            'packaging_params': {}, 'runtime_params': {},
                            'build_params': {}}


@pytest.mark.usefixtures('with_spam_builder_sig')
def test_file_arg_from_project_root():
    target = Target(builder_name='Spam')
    args_to_props(target, Plugin.builders['Spam'],
                  args=['my-spam', 'foo', 'bar'],
                  kwargs={'cat_list': '//lists/from-vet-4'})
    handle_typed_args(target, Plugin.builders['Spam'], 'spams')
    assert target.props == {'name': 'spams:my-spam', 'foo': 'foo',
                            'bar': 'bar', 'deps': [], 'cachable': True,
                            'cats': [],
                            'cat_list': path.join('lists', 'from-vet-4'),
                            'packaging_params': {}, 'runtime_params': {},
                            'build_params': {}}
