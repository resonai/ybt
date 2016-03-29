# -*- coding: utf-8 -*-

"""
yabt config
~~~~~~~~~~~

:copyright: (c) 2016 Yowza by Itamar Ostricher
:license: MIT, see LICENSE for more details.
"""


import os


BUILD_PROJ_FILE = 'yroot'
YCONFIG_FILE = 'yconfig'


class Config:

    attrs_from_args = frozenset((
        'build_file_name', 'default_target_name', 'cmd', 'targets',
        'builders_workspace_dir',
    ))

    def __init__(self, args, project_root_dir: str, work_dir: str):
        """
        :param project_root_dir: Absolute path to build project root directory.
        :param work_dir: Absolute path to working directory within project.
        """
        for slot in self.attrs_from_args:
            setattr(self, slot, getattr(args, slot))
        self.project_root = project_root_dir
        self.work_dir = work_dir

    def get_rel_work_dir(self):
        return os.path.relpath(self.work_dir, self.project_root)

    def get_project_build_file(self):
        return os.path.join(self.project_root, BUILD_PROJ_FILE)

    def get_build_file_path(self, build_module):
        is_root_module = os.path.abspath(build_module) == self.project_root
        return os.path.join(
            self.project_root, build_module,
            BUILD_PROJ_FILE if is_root_module else self.build_file_name)

    def get_workspace_path(self):
        return os.path.join(self.project_root, self.builders_workspace_dir)
