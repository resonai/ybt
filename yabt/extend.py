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
yabt Extend
~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from collections import defaultdict, namedtuple, OrderedDict
from enum import Enum
from functools import partial, wraps
import pkg_resources

from .logging import make_logger


logger = make_logger(__name__)


class Empty(type):
    pass


PropType = Enum('PropType', """str
                               numeric
                               bool
                               list
                               StrList
                               TargetName
                               Target
                               TargetList
                               File
                               FileList

                               untyped
                               """)


ArgSpec = namedtuple('ArgSpec', 'type default')


def evaluate_arg_spec(arg_spec):
    arg_type = PropType.untyped
    def_val = Empty
    if isinstance(arg_spec, tuple):
        if len(arg_spec) == 2:
            arg_name, second = arg_spec
            if isinstance(second, PropType):
                arg_type = second
            else:
                def_val = second
        elif len(arg_spec) == 3:
            arg_name, arg_type, def_val = arg_spec
    else:
        arg_name = arg_spec
    # TODO(itamar): better errors than asserts
    assert isinstance(arg_name, str)
    assert isinstance(arg_type, PropType)
    # also check validity of def_val?
    return arg_name, ArgSpec(arg_type, def_val)


class Builder:

    def __init__(self):
        self.sig = None
        self.func = None
        self.docstring = None
        self.min_positional_args = 1  # the `name`

    def register_sig(self, builder_name: str, sig: list, docstring: str):
        if self.sig is not None:
            raise KeyError('{} already registered a signature!'
                           .format(builder_name))
        self.sig = OrderedDict(name=ArgSpec(PropType.TargetName, Empty))
        self.docstring = docstring
        kwargs_section = False
        for arg_spec in sig:
            arg_name, sig_spec = evaluate_arg_spec(arg_spec)
            # `deps` is special - if part of the signature,
            # it must be TargetList - so if it's not - raise
            if arg_name == 'deps' and sig_spec.type != PropType.TargetList:
                raise TypeError(
                    '{} signature attmpted to define `deps` as {} - must be '
                    'TargetList'.format(builder_name, sig_spec.type))
            self.sig[arg_name] = sig_spec
            if sig_spec.default == Empty:
                if kwargs_section:
                    # TODO(itamar): how to give syntax error source annotation?
                    # (see: http://stackoverflow.com/questions/33717804)
                    raise SyntaxError(
                        'non-default argument follows default argument')
                self.min_positional_args += 1
            else:
                kwargs_section = True


class Plugin:

    builders = defaultdict(Builder)
    hooks = {
        'manipulate_target': {},
    }

    @classmethod
    def load_plugins(cls, unused_conf):
        # TODO(itamar): Support config semantics for explicitly enabling /
        # disabling builders, and not just picking up everything that's
        # installed.
        for entry_point in pkg_resources.iter_entry_points('yabt.builders'):
            entry_point.load()
            logger.debug('Loaded builder {0.name} from {0.module_name} '
                         '(dist {0.dist})', entry_point)
        logger.debug('Loaded {} builders', len(cls.builders))
        cls.validate()

    @classmethod
    def get_hooks_for_builder(cls, builder_name: str):
        for hook_name, hook_spec in Plugin.hooks.items():
            if builder_name in hook_spec:
                yield hook_name, hook_spec[builder_name]

    @classmethod
    def validate(cls):
        # TODO(itamar): validate stuff
        # 1. builders are functions with good signatures (name as first arg)
        # 2. hooks belong to existing builders
        pass

    @classmethod
    def remove_builder(cls, builder_name: str):
        """Remove a registered builder `builder_name`.

        No reason to use this except for tests.
        """
        cls.builders.pop(builder_name, None)
        for hook_spec in cls.hooks.values():
            hook_spec.pop(builder_name, None)


def register_builder_sig(builder_name, sig, docstring=None):
    Plugin.builders[builder_name].register_sig(builder_name, sig, docstring)
    logger.debug('Registered {} builder signature'.format(builder_name))


def register_build_func(builder_name):
    def register_decorator(build_func):
        if Plugin.builders[builder_name].func:
            raise KeyError('{} already registered a build function!'
                           .format(builder_name))
        Plugin.builders[builder_name].func = build_func
        logger.debug('Registered {0} builder signature from '
                     '{1.__module__}.{1.__name__}()', builder_name, build_func)

        @wraps(build_func)
        def builder_wrapper(*args, **kwrags):
            return build_func(*args, **kwrags)
        return builder_wrapper
    return register_decorator


def _register_hook(hook_name, builder_name):
    def register_decorator(hook_func):
        assert hook_name in Plugin.hooks
        Plugin.hooks[hook_name][builder_name] = hook_func
        logger.debug('Registered {0} hook for {1} builder from '
                     '{2.__module__}.{2.__name__}()',
                     hook_name, builder_name, hook_func)

        @wraps(hook_func)
        def hook_wrapper(*args, **kwargs):
            return hook_func(*args, **kwargs)
        return hook_wrapper
    return register_decorator


register_manipulate_target_hook = partial(_register_hook, 'manipulate_target')
