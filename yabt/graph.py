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
yabt target graph
~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import networkx
from networkx.algorithms import dag

from .buildcontext import BuildContext
from .buildfile import process_build_file
from .config import Config
from .target import generate_build_modules, parse_target_selectors, split_name


def build_target_dep_graph(unused_conf: Config):
    dep_graph = networkx.DiGraph()
    for target_name, target_context in BuildContext.targets.items():
        dep_graph.add_node(target_name)
        for dep in target_context.target.deps:
            dep_graph.add_edge(target_name, dep)
    return dep_graph


def populate_targets_graph(conf: Config):
    # Process project root build file
    process_build_file(conf.get_project_build_file(), conf)
    targets_to_prune = set(BuildContext.targets.keys())
    if conf.targets:
        print('targets:', conf.targets)
        # TODO(itamar): Figure out how to support a target selector that is a
        #   parent directory which isn't a build module, but contains build
        #   modules (e.g., `ybt tree yapi` from the `dag` test root).
        seeds = parse_target_selectors(conf.targets, conf)
        print('seeds', seeds)
    else:
        default_target = ':{}'.format(conf.default_target_name)
        print('searching for default target {}'.format(default_target))
        if default_target not in BuildContext.targets:
            raise RuntimeError(
                'No default target found, and no target selector specified')
        seeds = [default_target]

    # Crawl rest of project from seeds
    for seed in seeds:
        # print('SEED', seed)
        if seed in BuildContext.targets:
            #
            if seed in targets_to_prune:
                targets_to_prune.remove(seed)
            seeds.extend(BuildContext.targets[seed].target.deps)
        else:
            if seed == '**:*':
                # Adding all build modules under current working directory as
                # seeds
                seeds.extend(generate_build_modules('.', conf))
                continue
            build_module, target_name = seed.split(':', 1)
            # print(build_module, target_name)
            process_build_file(conf.get_build_file_path(build_module), conf)
            # Parsed build file with this seed target - add its dependencies as
            # seeds
            if target_name == '*':
                # It's a wildcard - add all targets from build module
                for module_target in (
                        BuildContext.targets_by_module[build_module]):
                    seeds.extend(
                        BuildContext.targets[module_target].target.deps)
            else:
                if seed not in BuildContext.targets:
                    raise RuntimeError(
                        'Don\'t know how to make `{}\''.format(seed))
                #
                for module_target in (
                        BuildContext.targets_by_module[build_module]):
                    targets_to_prune.add(module_target)
                targets_to_prune.remove(seed)
                seeds.extend(BuildContext.targets[seed].target.deps)
        # print('PRUNE', targets_to_prune)
        # TODO(itamar): Write tests that pruning is *ALWAYS* correct!
        # e.g., not pruning things it shouldn't (like when targets are in prune
        # list when loaded initially, but should be removed later because a
        # target loaded later required them).

    # Pruning, after parsing is done
    targets_to_prune.update(
        target_name for target_name in BuildContext.targets.keys()
        if split_name(target_name).startswith('@'))
    for target_name in targets_to_prune:
        BuildContext.remove_target(target_name)

    BuildContext.target_graph = build_target_dep_graph(conf)
    assert dag.is_directed_acyclic_graph(BuildContext.target_graph)


def topological_sort(graph: networkx.DiGraph, reverse: bool=True):
    yield from dag.topological_sort(graph, reverse=reverse)
