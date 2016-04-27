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

# pylint: disable=invalid-name, unused-argument

"""
yabt Python Builders
~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)


register_builder_sig(
    'PythonPackage',
    [('package', PT.str),
     ('version', PT.str, None),
     ('deps', PT.TargetList, None)
     ])


def format_req_specifier(target):
    if target.props.version:
        return '{0.package}=={0.version}'.format(target.props)
    return '{0.package}'.format(target.props)


@register_build_func('PythonPackage')
def python_package_builder(build_context, target):
    print('Fetch and cache PyPI package', target)


@register_manipulate_target_hook('PythonPackage')
def python_package_manipulate_target(build_context, target):
    target.tags.add('pip-installable')


register_builder_sig(
    'Python',
    [('deps', PT.TargetList, None),
     ('sources', PT.FileList, None),
     ('data', PT.FileList, None)
     ])


@register_build_func('Python')
def python_builder(build_context, target):
    print('Build Python', target)
    # TODO(itamar): auto-add __init__.py in dirs of sources if they exist
    target.artifacts['app'].extend(target.props.sources)
    target.artifacts['app'].extend(target.props.data)
