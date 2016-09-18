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

from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..logging import make_logger
from ..utils import yprint
import os


logger = make_logger(__name__)


register_builder_sig(
    'Proto',
    [  # ('deps', PT.TargetList, None),
     ('output_path', PT.str),
     ('sources', PT.FileList, None),
     ('in_buildenv', PT.Target, None),
     ('cmd_env', None),

     ])


@register_build_func('Proto')
def proto_builder(build_context, target):
    yprint(build_context.conf, 'Build (run) Proto', target)
    workspace_dir = build_context.get_workspace('proto', target.name)
    output_dir = './{}'.format(target.props.output_path)
    if(not os.path.isdir(output_dir)):
        build_context.run_in_buildenv(
            target.props.in_buildenv, [
                'mkdir',
                # '--proto_path=build/gen',
                'out'], target.props.cmd_env)
    build_context.run_in_buildenv(
        target.props.in_buildenv, [
          'protoc',
          # '--proto_path=build/gen',
          '--cpp_out', output_dir,
          '--python_out', output_dir,
          target.props.sources[0]], target.props.cmd_env)


@register_manipulate_target_hook('Proto')
def ext_command_manipulate_target(build_context, target):
    target.buildenv = target.props.in_buildenv
