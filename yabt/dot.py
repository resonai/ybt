# -*- coding: utf-8 -*-

# Copyright 2019 Resonai Ltd. All rights reserved
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
Creates the dot graph
~~~~~~~~~~~~~~~~~

:author: Dana Shamir
"""


from networkx.algorithms import descendants

from .caching import load_target_from_cache
from .config import Config


TARGETS_COLORS = {'Python': 'red', 'PythonTest': 'pink',
                  'PythonPackage': 'purple', 'CppLib': 'blue',
                  'AptPackage': 'brown4', 'CostomInstaller': 'brown',
                  'Proto': 'green'}


def write_dot(build_context, conf: Config, out_f):
    """Write build graph in dot format to `out_f` file-like object."""
    buildenvs = set(
        target.buildenv for target in build_context.targets.values()
        if target.buildenv is not None)
    buildenv_targets = set(buildenvs)
    for buildenv in buildenvs:
        buildenv_targets = buildenv_targets.union(
            descendants(build_context.target_graph, buildenv))
    out_f.write('strict digraph  {\n')
    for node in build_context.target_graph.nodes:
        if conf.show_buildenv_deps or node not in buildenv_targets:
            cached = load_target_from_cache(
                build_context.targets[node], build_context)[0]
            fillcolor = 'fillcolor="grey",style=filled' if cached else ''
            color = TARGETS_COLORS.get(
                build_context.targets[node].builder_name, 'black')
            out_f.write('  "{}" [color="{}",{}];\n'.format(node, color,
                                                           fillcolor))
    out_f.writelines('  "{}" -> "{}";\n'.format(u, v)
                     for u, v in build_context.target_graph.edges
                     if conf.show_buildenv_deps or
                     (u not in buildenv_targets and v not in buildenv_targets))
    out_f.write('}\n\n')
