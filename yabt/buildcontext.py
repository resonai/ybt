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
yabt Build context module
~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from collections import defaultdict
import os
import pkg_resources as pkgr

from ostrich.utils.text import get_safe_path

from . import target


class TargetContext:  # pylint: disable=too-few-public-methods
    def __init__(self, target_inst, builder_inst, builder_context):
        self.target = target_inst
        self.builder = builder_inst
        self.context = builder_context


class BuildContext:

    _builders = {}
    targets = {}
    targets_by_module = defaultdict(set)
    target_graph = None
    # processed_build_files = set()
    active_builders = None

    @classmethod
    def get_active_builders(cls, unused_conf):
        # TODO(itamar): Support config semantics for explicitly enabling /
        # disabling builders, and not just picking up everything that's
        # installed.
        if cls.active_builders is None:
            cls.active_builders = [
                ep.load()
                for ep in pkgr.iter_entry_points(group='yabt.builders')]
            print('Loaded {} builders'.format(len(cls.active_builders)))
        return cls.active_builders

    def __init__(self, conf, build_file_path):
        self.conf = conf
        self.build_file_path = build_file_path
        for builder_class in self.get_active_builders(self.conf):
            builder_inst = builder_class(self)
            for alias in builder_class.get_builder_aliases():
                self._builders[alias] = builder_inst

    def get_build_module(self):
        relpath = os.path.relpath(self.build_file_path, self.conf.project_root)
        return os.path.split(os.path.normpath(relpath))[0]

    def get_workspace(self, *parts):
        workspace_dir = os.path.join(self.conf.get_workspace_path(),
                                     *(get_safe_path(part)
                                       for part in parts))
        if not os.path.isdir(workspace_dir):
            # exist_ok=True in case of concurrent creation of the same
            # workspace
            os.makedirs(workspace_dir, exist_ok=True)
        return workspace_dir

    @classmethod
    def walk_target_graph(cls, target_names):
        for target_name in target_names:
            yield cls.targets[target_name].target
            yield from cls.walk_target_graph(
                cls.target_graph.neighbors_iter(target_name))

    def register_target(self, target_inst, builder_inst):
        if target_inst.name in self.targets:
            first = self.targets[target_inst.name]
            raise NameError(
                'Target with name "{}" ({} from "{}") already exists - '
                'defined first as {} from "{}"'.format(
                    target_inst.name, builder_inst.__class__.__name__,
                    self.build_file_path, first.builder.__class__.__name__,
                    first.context.build_file_path))
        target_context = TargetContext(target_inst, builder_inst, self)
        self.targets[target_inst.name] = target_context
        self.targets_by_module[target.split_build_module(target_inst.name)] \
            .add(target_inst.name)

    @classmethod
    def remove_target(cls, target_name):
        if target_name in cls.targets:
            del cls.targets[target_name]
        if target.split_build_module(target_name) in cls.targets_by_module:
            cls.targets_by_module[target.split_build_module(target_name)] \
                .remove(target_name)

    @classmethod
    def get_target_extraction_context(cls):
        return {builder_alias: builder_inst.extract_target
                for builder_alias, builder_inst in cls._builders.items()}
