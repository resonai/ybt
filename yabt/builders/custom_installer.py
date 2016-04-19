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
yabt Custom Installer Builder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import os
from os.path import basename, join

import git
from git import InvalidGitRepositoryError, NoSuchPathError

from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..target_utils import split_name


register_builder_sig(
    'CustomInstaller',
    [('uri', PT.str),
     ('script', PT.File),
     ('deps', PT.TargetList, None),
     ('uri_type', PT.str, None),
     ])


@register_build_func('CustomInstaller')
def custom_installer_builder(build_context, target):
    print('Fetch and cache custom installer package', target)
    # clone the repository under a private builder workspace
    workspace_dir = build_context.get_workspace('CustomInstaller', target.name)
    target_name = split_name(target.name)
    script_name = basename(target.props.script)
    package_dir = join(workspace_dir, target_name)
    install_script = join(workspace_dir, script_name)
    try:
        repo = git.Repo(package_dir)
    except (InvalidGitRepositoryError, NoSuchPathError):
        repo = git.Repo.clone_from(target.props.uri, package_dir)
    # link the install script in the workspace dir
    try:
        os.remove(install_script)
    except:
        pass
    os.link(join(build_context.conf.project_root, target.props.script),
            install_script)
    assert repo.working_tree_dir == package_dir
    target.props.workspace = workspace_dir
    target.props.rel_dir_script = (basename(workspace_dir), script_name)


@register_manipulate_target_hook('CustomInstaller')
def custom_installer_manipulate_target(build_context, target):
    target.tags.add('custom-installer')
