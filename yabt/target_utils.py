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
yabt target utils module
~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from collections import defaultdict
from hashlib import md5
import json
from os.path import join, normpath
from pathlib import PurePath
import types

from munch import Munch
from ostrich.utils.collections import listify
from ostrich.utils.text import get_safe_path

from .artifact import ArtifactStore
from .extend import Plugin, PropType as PT
from .compat import walk
from .config import Config
from .utils import hash_tree, norm_proj_path


_TARGET_NAMES_WHITELIST = frozenset(('*', '@default'))


def validate_name(target_name):
    try:
        if (target_name in _TARGET_NAMES_WHITELIST or
                target_name == get_safe_path(target_name)):
            return target_name
    except ValueError:
        pass
    raise ValueError("Invalid target name: `{}'".format(target_name))


def split(target_name):
    """Split a target name. Returns a tuple "(build_module, name)".

    The split is on the first `:`.
    Extra `:` are considered part of the name.
    """
    return target_name.split(':', 1)


def split_build_module(target_name):
    """Return the build module component of a target name."""
    return split(target_name)[0]


def split_name(target_name):
    """Return the name component of a target name."""
    return split(target_name)[1]


def norm_name(build_module: str, target_name: str):
    """Return a normalized canonical target name for the `target_name`
       observed in build module `build_module`.

    A normalized canonical target name is of the form "<build module>:<name>",
    where <build module> is the relative normalized path from the project root
    to the target build module (POSIX), and <name> is a valid target name
    (see `validate_name()`).
    """
    if ':' not in target_name:
        raise ValueError(
            "Must provide fully-qualified target name (with `:') to avoid "
            "possible ambiguity - `{}' not valid".format(target_name))

    mod, name = split(target_name)
    return '{}:{}'.format(
        PurePath(norm_proj_path(mod, build_module)).as_posix().strip('.'),
        validate_name(name))


def expand_target_selector(target_selector: str, conf: Config):
    """Return a normalized target name (where `**:*` is the normalized form of
       itself).

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
        standard POSIX relative path construction.
    """
    if target_selector == '**:*':
        return target_selector
    if ':' not in target_selector:
        target_selector += ':*'
    build_module, target_name = split(target_selector)
    build_module = normpath(join(conf.get_rel_work_dir(), build_module))
    return '{}:{}'.format(PurePath(build_module).as_posix().strip('.'),
                          validate_name(target_name))


def parse_target_selectors(target_selectors: list, conf: Config):
    return [expand_target_selector(target_selector, conf)
            for target_selector in target_selectors]


def hashify_targets(targets: list, build_context) -> list:
    """Return sorted hashes of `targets`."""
    return sorted(build_context.targets[target_name].hash(build_context)
                  for target_name in listify(targets))


def hashify_files(files: list) -> dict:
    """Return mapping from file path to file hash."""
    return {filepath.replace('\\', '/'): hash_tree(filepath)
            for filepath in listify(files)}


def process_prop(prop_type: PT, value, build_context):
    """Return a cachable representation of the prop `value` given its type."""
    if prop_type in (PT.Target, PT.TargetList):
        return hashify_targets(value, build_context)
    elif prop_type in (PT.File, PT.FileList):
        return hashify_files(value)
    return value


class Target(types.SimpleNamespace):  # pylint: disable=too-few-public-methods

    _prop_json_blacklist = frozenset((
        'cachable',
        'copy_generated_to',
        'image_caching_behavior',
    ))
    _prop_json_testlist = frozenset((
        'test_flags',
    ))

    def __init__(self, builder_name):
        super().__init__(
            name=None,
            builder_name=builder_name,
            props=Munch(),
            deps=None,
            buildenv=None,
            tags=set(),
            artifacts=ArtifactStore(),
            summary={
                'build_time': None,
                'created': None,
                'accessed': None,
            },
            info={
                'test_time': None,
                'fail_count': 0,
            },
            is_dirty=False,
            tested={},
            _hash=None,
            _json=None,
            _test_json=None,
        )

    def __repr__(self):
        keys = ['name', 'builder_name', 'props', 'deps', 'buildenv', 'tags']
        items = ('{}={!r}'.format(k, self.__dict__[k]) for k in keys)
        return '{}({})'.format(type(self).__name__, ', '.join(items))

    def compute_json(self, build_context):
        """Compute and store a JSON serialization of this target for caching
           purposes.

        The serialization includes:
        - The build flavor
        - The builder name
        - Target tags
        - Hashes of target dependencies & buildenv
        - Processed props (where target props are replaced with their hashes,
          and file props are replaced with mapping from file name to its hash)

        It specifically does NOT include:
        - Artifacts produced by the target

        The target name is currently included, although it would be better off
        to leave it out, and allow targets to be renamed without affecting
        their caching status (if it's just a rename).
        It is currently included because it's the easy way to account for the
        fact that when cached artifacts are restored, their path may be a
        function of the target name in non-essential ways (such as a workspace
        dir name).
        """
        props = {}
        test_props = {}
        for prop in self.props:
            if prop in self._prop_json_blacklist:
                continue
            sig_spec = Plugin.builders[self.builder_name].sig.get(prop)
            if sig_spec is None:
                continue
            if prop in self._prop_json_testlist:
                test_props[prop] = process_prop(sig_spec.type,
                                                self.props[prop],
                                                build_context)
            else:
                props[prop] = process_prop(sig_spec.type, self.props[prop],
                                           build_context)
        json_dict = dict(
            # TODO: avoid including the name in the hashed json...
            name=self.name,
            builder_name=self.builder_name,
            deps=hashify_targets(self.deps, build_context),
            props=props,
            buildenv=hashify_targets(self.buildenv, build_context),
            tags=sorted(list(self.tags)),
            flavor=build_context.conf.flavor,  # TODO: any other conf args?
            # yabt_version=__version__,  # TODO: is this needed?
        )
        json_test_dict = dict(
            props=test_props,
        )

        self._json = json.dumps(json_dict, sort_keys=True, indent=4)
        self._test_json = json.dumps(json_test_dict, sort_keys=True, indent=4)

    def json(self, build_context) -> str:
        """Return JSON serialization of this target for caching purposes."""
        if self._json is None:
            self.compute_json(build_context)
        return self._json

    def test_json(self, build_context) -> str:
        """Return JSON serialization of the test target for caching purposes.
        """
        if self._test_json is None:
            self.compute_json(build_context)
        return self._test_json

    def compute_hash(self, build_context):
        """Compute and store the hash of this target for caching purposes.

        The hash is computed over the target JSON representation.
        """
        m = md5()
        m.update(self.json(build_context).encode('utf8'))
        self._hash = m.hexdigest()
        m = md5()
        m.update(self.test_json(build_context).encode('utf8'))
        self._test_hash = m.hexdigest()

    def hash(self, build_context) -> str:
        """Return the hash of this target for caching purposes."""
        if self._hash is None:
            self.compute_hash(build_context)
        return self._hash

    def test_hash(self, build_context) -> str:
        """Return the hash of this test target for caching purposes."""
        if self._test_hash is None:
            self.compute_hash(build_context)
        return self._test_hash


class ImageCachingBehavior(types.SimpleNamespace):

    def __init__(self, name, tag, behavior: dict = {}):
        super().__init__(
            remote_image='{}:{}'.format(
                behavior.get('remote_image_name', name),
                behavior.get('remote_image_tag', tag)),
            pull_if_not_cached=behavior.get('pull_if_not_cached', False),
            pull_if_cached=behavior.get('pull_if_cached', False),
            allow_build_if_not_cached=behavior.get(
                'allow_build_if_not_cached', True),
            skip_build_if_cached=behavior.get('skip_build_if_cached', False),
            push_image_after_build=behavior.get(
                'push_image_after_build', False),
        )
