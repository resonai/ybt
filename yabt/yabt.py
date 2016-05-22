#!/usr/bin/env python3
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
yabt
~~~~

:author: Itamar Ostricher
"""


from collections import namedtuple
import sys

from .buildcontext import BuildContext
from .cli import init_and_get_conf
from .config import Config, BUILD_PROJ_FILE
from .docker import build_docker_image
from .extend import Plugin
from .graph import populate_targets_graph, topological_sort
from .target_utils import parse_target_selectors, split


YabtCommand = namedtuple('YabtCommand', ['func', 'requires_project'])


def cmd_version(unused_conf):
    """Print out version information about YABT and detected builders."""
    import pkg_resources
    from . import __oneliner__, __version__
    print('This is {} version {}, imported from {}'
          .format(__oneliner__, __version__, __file__))
    if len(Plugin.builders) > 0:
        print('setuptools registered builders:')
    for entry_point in pkg_resources.iter_entry_points('yabt.builders'):
        print('  {0.module_name}.{0.name} (dist {0.dist})'.format(entry_point))


# def cmd_help(unused_conf):
#   parser.print_help()
#   sys.exit(0)


def cmd_list(unused_conf: Config):
    """Print out information on loaded builders and hooks."""
    for name, builder in sorted(Plugin.builders.items()):
        if builder.func:
            print('+- {0:16s} implemented in {1.__module__}.{1.__name__}()'
                  .format(name, builder.func))
        else:
            print('+- {0:16s} loaded with no builder function'.format(name))
        for hook_name, hook_func in sorted(Plugin.get_hooks_for_builder(name)):
            print('  +- {0} hook implemented in '
                  '{1.__module__}.{1.__name__}()'
                  .format(hook_name, hook_func))


def cmd_build(conf: Config):
    """Build requested targets, and their dependencies."""
    build_context = BuildContext(conf)
    populate_targets_graph(build_context, conf)
    # # pass 1: prepare BuildEnv images
    # if conf.default_buildenv_base_image:
    #     # TODO(itamar): generate random tag to avoid conflicts if running
    #     # multiple instances concurrently
    #     build_docker_image(
    #         build_context,
    #         name='ybt-buildenv',
    #         tag='latest',
    #         base_image=build_context.targets[conf.default_buildenv_base_image],
    #         deps=[build_context.targets[target_name] for target_name in
    #               topological_sort(build_context.target_graph)],
    #         no_artifacts=True)
    #     build_context.register_buildenv_image('ybt-buildenv',
    #                                           'ybt-buildenv:latest')
    # pass 2: build
    for target_name in topological_sort(build_context.target_graph):
        target = build_context.targets[target_name]
        build_context.build_target(target)


def cmd_tree(conf: Config):
    """Print out a neat targets dependency tree based on requested targets."""
    build_context = BuildContext(conf)
    populate_targets_graph(build_context, conf)

    def print_target_with_deps(target, depth=2):
        print('{: >{}}{}'.format('+-', depth, target.name))
        for dep in sorted(
                build_context.target_graph.neighbors_iter(target.name)):
            print_target_with_deps(build_context.targets[dep], depth + 2)

    if conf.targets:
        for target_name in sorted(parse_target_selectors(conf.targets, conf)):
            mod, name = split(target_name)
            if name == '*':
                for target_name in sorted(
                        build_context.targets_by_module[mod]):
                    print_target_with_deps(build_context.targets[target_name])
            else:
                print_target_with_deps(build_context.targets[target_name])
    else:
        for _, target in sorted(build_context.targets.items()):
            print_target_with_deps(target)


def main():
    """Main `ybt` console script entry point - run YABT from command-line."""
    conf = init_and_get_conf()
    handlers = {
        'build': YabtCommand(func=cmd_build, requires_project=True),
        'tree': YabtCommand(func=cmd_tree, requires_project=True),
        'version': YabtCommand(func=cmd_version, requires_project=False),
        'list-builders': YabtCommand(func=cmd_list, requires_project=False),
    }
    command = handlers[conf.cmd]
    if command.requires_project and not conf.in_yabt_project():
        print('fatal: Not a YABT project (or any of the parent directories): '
              '{}'.format(BUILD_PROJ_FILE))
        sys.exit(1)
    command.func(conf)


if __name__ == '__main__':
    main()
