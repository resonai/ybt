# -*- coding: utf-8 -*-

"""
yabt base builder
~~~~~~~~~~~~~~~~~

:copyright: (c) 2016 Yowza by Itamar Ostricher
:license: MIT, see LICENSE for more details.
"""


from . import target


class BaseBuilder:

    def __init__(self, build_context):
        self._context = build_context

    # def extract_target(self, *args, **kwargs):
    #     raise NotImplementedError(self.__class__.__name__)

    def build(self, target_inst):  # pylint: disable=unused-argument
        raise NotImplementedError(self.__class__.__name__)

    def get_workspace(self, *parts):
        """Return a path to a private builder-specific workspace dir.
           Create sub-tree of dirs using strings from `parts` inside workspace,
           and return full path to innermost directory.

        Upon returning successfully, the directory will exist (potentially
        changed to a safe FS name), even if it didn't exist before, including
        any intermediate parent directories.
        """
        return self._context.get_workspace(self.__class__.__name__, *parts)

    def get_target_by_depname(self, dep):
        return (self._context.targets[target.norm_name(self._context, dep)]
                .target)

    def walk_target_graph(self, node_names):
        yield from self._context.walk_target_graph(node_names)
