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
yabt config
~~~~~~~~~~~

:author: Itamar Ostricher
"""


import os
from pathlib import Path

from ostrich.utils.collections import listify
from ostrich.utils.text import get_safe_path

from .extend import Plugin
from .logging import configure_logging
from .scm import ScmManager
from .utils import norm_proj_path, search_for_parent_dir


BUILD_PROJ_FILE = 'YRoot'
YCONFIG_FILE = 'YConfig'
YSETTINGS_FILE = 'YSettings'


class Config:
    """Runtime Config info class"""

    attrs_from_args = frozenset((
        'artifacts_metadata_file',
        'bin_output_dir',
        'build_base_images',
        'build_file_name',
        'builders_workspace_dir',
        'cmd',
        'default_target_name',
        'docker_volume',
        'flavor',
        'force_pull',
        'jobs',
        'non_interactive',
        'offline',
        'output_dot_file',
        'push',
        'targets',
        'verbose',
        'with_tini_entrypoint',
        # logging-related
        'loglevel', 'logtostderr', 'logtostdout',
    ))

    def __init__(self, args, project_root_dir: str, work_dir: str,
                 settings_module=None):
        """
        :param project_root_dir: Absolute path to build project root directory.
        :param work_dir: Absolute path to working directory within project.
        """
        for slot in self.attrs_from_args:
            setattr(self, slot, getattr(args, slot))
        self.docker_pull_cmd = args.docker_pull_cmd.split()
        self.docker_push_cmd = args.docker_push_cmd.split()
        configure_logging(self)
        self.project_root = project_root_dir
        self.work_dir = work_dir
        self.scm_provider = str(args.scm_provider).lower()
        self.scm = ScmManager.get_provider(self.scm_provider, self)
        Plugin.load_plugins(self)
        self.deleted_dirs = set()
        self.settings = settings_module
        self.common_conf = {}
        self.flavor_conf = {}
        self.flavor_dir = get_safe_path('flavor__all__' if self.flavor is None
                                        else '{}_flavor'.format(self.flavor))

    def in_yabt_project(self) -> bool:
        return self.project_root is not None

    def get_rel_work_dir(self) -> str:
        return os.path.relpath(self.work_dir, self.project_root)

    def get_project_build_file(self) -> str:
        return os.path.join(self.project_root, BUILD_PROJ_FILE)

    def get_build_file_path(self, build_module) -> str:
        """Return a full path to the build file of `build_module`.

        The returned path will always be OS-native, regardless of the format
        of project_root (native) and build_module (with '/').
        """
        project_root = Path(self.project_root)
        build_module = norm_proj_path(build_module, '')
        return str(project_root / build_module /
                   (BUILD_PROJ_FILE if '' == build_module
                    else self.build_file_name))

    def get_workspace_path(self) -> str:
        return os.path.join(
            self.project_root, self.builders_workspace_dir, self.flavor_dir)

    def get_bin_path(self) -> str:
        return os.path.join(self.project_root, self.bin_output_dir)

    def host_to_buildenv_path(self, host_path: str) -> str:
        host_path, project_root = Path(host_path), Path(self.project_root)
        # TODO: windows-containers?
        return '/'.join([
            '/project',
            host_path.resolve().relative_to(project_root).as_posix()])

    def get(self, param: str, fallback: str) -> str:
        common_val, flavor_val = None, None
        if self.common_conf:
            common_val = self.common_conf.get(param)
        if self.flavor_conf:
            flavor_val = self.flavor_conf.get(param)
        if common_val is None and flavor_val is None:
            return fallback
        if flavor_val is not None:
            if isinstance(flavor_val, list):
                val = []
                for el in flavor_val:
                    if el == '$*':
                        val.extend(listify(common_val))
                    else:
                        val.append(el)
                return val
            return flavor_val
        return common_val or fallback
