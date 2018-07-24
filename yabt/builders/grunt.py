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

# pylint: disable=invalid-name, unused-argument

"""
yabt Grunt builder
~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import os

from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..logging import make_logger
from ..target_utils import split_build_module
from ..utils import yprint


logger = make_logger(__name__)


register_builder_sig(
    'Grunt',
    [('in_buildenv', PT.Target, None),
     ('grunt_tasks', PT.StrList, None),
     ('cmd_env', None),
     ('work_dir', None),
     ],
    # not cachable by default, since in general this builder doesn't know how
    # to keep track of its artifacts
    cachable=False)


@register_build_func('Grunt')
def grunt_builder(build_context, target):
    yprint(build_context.conf, 'Build (run) Grunt', target)
    # npm_links = [dep.props.package for dep in
    #              build_context.walk_target_deps_topological_order(target)
    #              if ('npm-installable' in dep.tags and
    #                  dep.props.global_install)]
    work_dir = (target.props.work_dir if target.props.work_dir
                else split_build_module(target.name))
    logger.debug('Cleaning ".tmp" directory')
    build_context.run_in_buildenv(
        target.props.in_buildenv, ['rm', '-rf', '.tmp'],
        target.props.cmd_env, work_dir, auto_uid=False)
    yprint(build_context.conf, 'Running "npm install" in {}'.format(work_dir))
    build_context.run_in_buildenv(
        target.props.in_buildenv, ['npm', 'install'],
        target.props.cmd_env, work_dir, auto_uid=False)
    yprint(build_context.conf,
           'Running "bower install" in {}'.format(work_dir))
    build_context.run_in_buildenv(
        target.props.in_buildenv, ['bower', 'install', '--allow-root'],
        target.props.cmd_env, work_dir, auto_uid=False)
    grunt_cmd = ['grunt'] + target.props.grunt_tasks
    yprint(build_context.conf,
           'Running "{}" in {}'.format(' '.join(grunt_cmd), work_dir))
    build_context.run_in_buildenv(
        target.props.in_buildenv, grunt_cmd,
        target.props.cmd_env, work_dir, auto_uid=False)
    logger.debug('Fix grunt output ownership')
    # TODO(itamar): Don't hardcode output dir here... ("dist")
    build_context.run_in_buildenv(
        target.props.in_buildenv,
        ['chown', '-R', '{}:{}'.format(os.getuid(), os.getgid()), 'dist'],
        target.props.cmd_env, work_dir, auto_uid=False)
    # TODO(itamar): way to describe the artifacts of the external command,
    # so it can be used by dependent targets, and cached in some smart way


@register_manipulate_target_hook('Grunt')
def grunt_manipulate_target(build_context, target):
    target.buildenv = target.props.in_buildenv
