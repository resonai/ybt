#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
yabt
~~~~

:copyright: (c) 2016 Yowza by Itamar Ostricher
:license: MIT, see LICENSE for more details.
"""


from .buildcontext import BuildContext
from .cli import init_and_get_conf
from .config import Config
from .graph import populate_targets_graph, topological_sort


def cmd_version(unused_conf):
    import pkg_resources
    from . import __oneliner__, __version__
    print('This is {} version {}, imported from {}'
          .format(__oneliner__, __version__, __file__))
    printed_title = False
    for ep in pkg_resources.iter_entry_points(group='yabt.builders'):
        if not printed_title:
            print('setuptools registered builders:')
            printed_title = True
        print('  {0.module_name}.{0.name} (dist {0.dist})'.format(ep))


# def cmd_help(unused_conf):
#   parser.print_help()
#   sys.exit(0)


def cmd_build(conf: Config):
    populate_targets_graph(conf)
    for target_name in topological_sort(BuildContext.target_graph):
        target_context = BuildContext.targets[target_name]
        target_context.builder.build(target_context.target)


def cmd_tree(conf: Config):
    populate_targets_graph(conf)

    def print_target_with_deps(target_context, depth=2):
        print('{: >{}}{}'.format('+-', depth, target_context.target.name))
        for dep in sorted(
                BuildContext.target_graph.neighbors_iter(
                    target_context.target.name)):
            print_target_with_deps(BuildContext.targets[dep], depth + 2)
    for _, target_context in sorted(BuildContext.targets.items()):
        print_target_with_deps(target_context)


def main():
    conf = init_and_get_conf()
    handlers = {
        'build': cmd_build,
        'tree': cmd_tree,
        'version': cmd_version,
    }
    func = handlers[conf.cmd]
    func(conf)
    return 0


if __name__ == '__main__':
    main()
