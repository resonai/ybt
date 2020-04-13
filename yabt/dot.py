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

import re
from .caching import get_prebuilt_targets
from .config import Config
import networkx


TARGETS_COLORS = {'AptPackage': 'brown4',
                  'CppGTest': 'deepskyblue4',
                  'CppLib': 'blue',
                  'CppProg': 'cornflowerblue',
                  'CustomInstaller': 'brown',
                  'Proto': 'green',
                  'Python': 'red',
                  'PythonPackage': 'purple',
                  'PythonTest': 'pink'
                  }


def get_not_buildenv_targets(build_context):
    roots = [n for n, d in build_context.target_graph.in_degree() if d == 0]
    buildenvs = set(
        target.buildenv for target in build_context.targets.values()
        if target.buildenv is not None)
    visited = set()
    to_do = []
    for root in roots:
        if root not in buildenvs:
            visited.add(root)
            to_do.append(root)

    while to_do:
        node = to_do.pop(-1)
        for successor in build_context.target_graph.successors(node):
            if successor not in visited and successor not in buildenvs:
                visited.add(successor)
                to_do.append(successor)
    return visited


def dot_file_line_proc(nx_g, line):
    """ Parsing dot file line """
    l_s = re.split(r'\s*->\s*', line)
    if len(l_s) == 2:
        name = re.sub(r'\s+|;', '', l_s[0]).strip('\"')
        child_name = re.sub(r'\s+|;', '', l_s[1]).strip('\"')
        nx_g.add_edge(name, child_name)
    else:
        l_s = re.split(r'\s+', line, 2)
        if (not l_s[0]) & bool(l_s[1]):
            name = l_s[1].strip('\"')
            d_l = dict()
            for a_l in re.split(r'\[|,|\]|;|\n', l_s[2]):
                l_s = re.split('=', a_l)
                if len(l_s) == 2:
                    d_l.update({l_s[0].strip('\"'): l_s[1].strip('\"')})
            nx_g.add_node(name, **d_l)


def load_dot(in_fname):
    """ Read graph from dot format """
    in_f = open(in_fname, 'r')
    nx_g = networkx.DiGraph()
    for line in in_f:
        dot_file_line_proc(nx_g, line)
    in_f.close()
    return nx_g


def write_dot(build_context, conf: Config, out_f):
    """Write build graph in dot format to `out_f` file-like object."""
    not_buildenv_targets = get_not_buildenv_targets(build_context)
    prebuilt_targets = get_prebuilt_targets(build_context)
    out_f.write('strict digraph  {\n')
    for node in build_context.target_graph.nodes:
        if conf.show_buildenv_deps or node in not_buildenv_targets:
            cached = node in prebuilt_targets
            fillcolor = 'fillcolor="grey",style=filled' if cached else ''
            color = TARGETS_COLORS.get(
                build_context.targets[node].builder_name, 'black')
            out_f.write('  "{}" [color="{}",{}];\n'.format(node, color,
                                                           fillcolor))
    out_f.writelines('  "{}" -> "{}";\n'.format(u, v)
                     for u, v in build_context.target_graph.edges
                     if conf.show_buildenv_deps or
                     (u in not_buildenv_targets and v in not_buildenv_targets))
    out_f.write('}\n\n')
