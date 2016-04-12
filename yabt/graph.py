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
from .buildfile_parser import process_build_file
from .config import Config
from .logging import make_logger
from .target_utils import generate_build_modules
from .target_utils import parse_target_selectors


logger = make_logger(__name__)


def build_target_dep_graph(build_context: BuildContext, unused_conf: Config):
    build_context.target_graph = networkx.DiGraph()
    for target_name, target in build_context.targets.items():
        build_context.target_graph.add_node(target_name)
        for dep in target.deps:
            build_context.target_graph.add_edge(target_name, dep)


def populate_targets_graph(build_context: BuildContext, conf: Config):
    # Process project root build file
    process_build_file(conf.get_project_build_file(), build_context, conf)
    targets_to_prune = set(build_context.targets.keys())
    if conf.targets:
        print('targets:', conf.targets)
        # TODO(itamar): Figure out how to support a target selector that is a
        #   parent directory which isn't a build module, but contains build
        #   modules (e.g., `ybt tree yapi` from the `dag` test root).
        seeds = parse_target_selectors(conf.targets, conf)
        print('seeds', seeds)
    else:
        default_target = ':{}'.format(conf.default_target_name)
        logger.info('searching for default target {}', default_target)
        if default_target not in build_context.targets:
            raise RuntimeError(
                'No default target found, and no target selector specified')
        seeds = [default_target]

    # Crawl rest of project from seeds
    for seed in seeds:
        # print('SEED', seed)
        if seed in build_context.targets:
            #
            if seed in targets_to_prune:
                targets_to_prune.remove(seed)
            seeds.extend(build_context.targets[seed].deps)
        else:
            if seed == '**:*':
                # Adding all build modules under current working directory as
                # seeds
                seeds.extend(generate_build_modules('.', conf))
                continue
            build_module, target_name = seed.split(':', 1)
            # print(build_module, target_name)
            process_build_file(conf.get_build_file_path(build_module),
                               build_context, conf)
            # Parsed build file with this seed target - add its dependencies as
            # seeds
            if target_name == '*':
                # It's a wildcard - add all targets from build module
                # (and skip adding to targets_to_prune altogether)
                for module_target in (
                        build_context.targets_by_module[build_module]):
                    seeds.extend(
                        build_context.targets[module_target].deps)
            else:
                if seed not in build_context.targets:
                    raise RuntimeError(
                        'Don\'t know how to make `{}\''.format(seed))
                #
                for module_target in (
                        build_context.targets_by_module[build_module]):
                    targets_to_prune.add(module_target)
                targets_to_prune.remove(seed)
                seeds.extend(build_context.targets[seed].deps)
        # print('PRUNE', targets_to_prune)
        # TODO(itamar): Write tests that pruning is *ALWAYS* correct!
        # e.g., not pruning things it shouldn't (like when targets are in prune
        # list when loaded initially, but should be removed later because a
        # target loaded later required them).

    # Pruning, after parsing is done
    # (first, adding targets that are tagged as "prune-me" to prune list)
    targets_to_prune.update(
        target_name
        for target_name, target in build_context.targets.items()
        if 'prune-me' in target.tags)
    for target_name in targets_to_prune:
        build_context.remove_target(target_name)

    build_target_dep_graph(build_context, conf)
    assert dag.is_directed_acyclic_graph(build_context.target_graph)


def topological_sort(graph: networkx.DiGraph, reverse: bool=True):
    yield from dag.topological_sort(graph, reverse=reverse)
