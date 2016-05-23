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
yabt config
~~~~~~~~~~~

:author: Itamar Ostricher
"""


import os

from .extend import Plugin
from .logging import configure_logging
from .scm import ScmManager
from .utils import search_for_parent_dir


BUILD_PROJ_FILE = 'YRoot'
YCONFIG_FILE = 'YConfig'


class Config:
    """Runtime Config info class"""

    attrs_from_args = frozenset((
        'build_file_name', 'default_target_name', 'cmd', 'targets',
        'build_base_images', 'builders_workspace_dir', 'force_pull',
        'offline', 'push', 'loglevel', 'logtostderr', 'logtostdout',
    ))

    def __init__(self, args, project_root_dir: str, work_dir: str):
        """
        :param project_root_dir: Absolute path to build project root directory.
        :param work_dir: Absolute path to working directory within project.
        """
        for slot in self.attrs_from_args:
            setattr(self, slot, getattr(args, slot))
        configure_logging(self)
        self.project_root = project_root_dir
        self.work_dir = work_dir
        self.scm_provider = str(args.scm_provider).lower()
        self.scm = ScmManager.get_provider(self.scm_provider, self)
        Plugin.load_plugins(self)

    def in_yabt_project(self) -> bool:
        return self.project_root is not None

    def get_rel_work_dir(self) -> str:
        return os.path.relpath(self.work_dir, self.project_root)

    def get_project_build_file(self) -> str:
        return os.path.join(self.project_root, BUILD_PROJ_FILE)

    def get_build_file_path(self, build_module) -> str:
        is_root_module = os.path.abspath(build_module) == self.project_root
        return os.path.join(
            self.project_root, build_module,
            BUILD_PROJ_FILE if is_root_module else self.build_file_name)

    def get_workspace_path(self) -> str:
        return os.path.join(self.project_root, self.builders_workspace_dir)
