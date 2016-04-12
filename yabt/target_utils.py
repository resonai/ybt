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
yabt target utils module
~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from os import walk
from os.path import join, normpath, relpath
import types

from neobunch import Bunch

from .config import Config


def split(target_name):
    return target_name.split(':', 1)


def split_build_module(target_name):
    return split(target_name)[0]


def split_name(target_name):
    return split(target_name)[1]


def norm_name(build_module: str, target_name: str):
    if ':' not in target_name:
        return '{}:{}'.format(build_module, target_name)

    mod, target_name = target_name.split(':', 1)
    if mod.startswith('.'):
        mod = normpath(join(build_module, mod))
        # TODO(itamar): assert that staying in project scope
    # elif mod.startswith('#'):
    #   mod = mod[1:]
    return '{}:{}'.format('' if mod == '.' else mod, target_name)


def expand_target_selector(target_selector: str, conf: Config):
    """

    Target specifier can be:

    - `**:*` - means to recursively build all targets under current
      working dir.
    - relative path from current working directory to another directory -
        means to build all targets defined in that build module.
    - a name of a target - means to build this named target in the build module
        in the current working directory.
    - a named target in another build module, with the build module given as a
        relative path from the current working directory (e.g. `../foo:bar`) -
        means to build the specified named target in the specified build
        module.
    - in cases where a relative path can be specified, it should be given using
        standard POSIX relative path construction. in addition, it is possible
        to prefix the path with `@` as a shortcut to the root of the project,
        so when the project root is at `~/foo`, and the working directory is
        `~/foo/bar`, then `@/baz:boom` would refer to a target named "boom" in
        the build module at `~/foo/baz` (just like `../baz:boom`).

    Return a normalized `(build_module_dir, target_name)` tuple.

    # In case if `**:*`, the returned tuple is `('**', '*')`
    #
    # Return a normalized target name (where `**:*` is the normalized form of
    # itself).
    """
    if target_selector == '**:*':
        return target_selector
    if ':' not in target_selector:
        target_selector += ':*'
    build_module, target_name = split(target_selector)
    if build_module.startswith('@'):
        build_module = normpath(relpath(
            build_module.replace('@', conf.project_root, 1),
            conf.project_root))
    else:
        build_module = normpath(join(conf.get_rel_work_dir(), build_module))
    return '{}:{}'.format('' if build_module == '.' else build_module,
                          target_name)


def parse_target_selectors(target_selectors: list, conf: Config):
    return [expand_target_selector(target_selector, conf)
            for target_selector in target_selectors]


def generate_build_modules(top: str, conf: Config):
    # TODO(itamar): add ignore marker files / flags
    for root, unused_dirs, files in walk(top):
        if conf.build_file_name in files:
            yield expand_target_selector(root, conf)


class Target(types.SimpleNamespace):  # pylint: disable=too-few-public-methods

    def __init__(self, builder_name):
        super().__init__(name=None, builder_name=builder_name, props=Bunch(),
                         deps=None, tags=set())

    def __repr__(self):
        keys = ['name', 'builder_name', 'props', 'deps', 'tags']
        items = ('{}={!r}'.format(k, self.__dict__[k]) for k in keys)
        return '{}({})'.format(type(self).__name__, ", ".join(items))
