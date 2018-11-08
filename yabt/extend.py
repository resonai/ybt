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

"""
yabt Extend
~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from collections import defaultdict, namedtuple, OrderedDict
from enum import Enum
from functools import partial, wraps
import pkg_resources

from ostrich.utils.collections import listify

from .logging import make_logger


logger = make_logger(__name__)


class Empty(type):
    pass


PropType = Enum('PropType', """str
                               numeric
                               bool
                               list
                               dict
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


INJECTED_ARGS = frozenset((
    'build_params', 'deps', 'cachable', 'license', 'attempts'
    'packaging_params', 'policies', 'runtime_params',
))


class Builder:

    def __init__(self):
        self.sig = None
        self.func = None
        self.test_func = None
        self.docstring = None
        self.min_positional_args = 1  # the `name`

    def register_sig(self, builder_name: str, sig: list, docstring: str,
                     cachable: bool=True, attempts=1):
        """Register a builder signature & docstring for `builder_name`.

        The input for the builder signature is a list of "sig-spec"s
        representing the builder function arguments.

        Each sig-spec in the list can be:
        1. A string. This represents a simple untyped positional argument name,
            with no default value.
        2. A 1-tuple with one string element. Same as #1.
        3. A 2-tuple with ('arg-name', arg_type). This represents a typed
            positional argument, if arg_type is an instance of PropType enum.
        4. A 2-tuple with ('arg-name', default_value). This represents an
            un-typed keyword argument with a default value.
        5. A 3-tuple with ('arg-name', arg_type, default_value). This
            represents a typed keyword argument with a default value,
            if arg_type is an instance of PropType enum.

        In addition to the args specified in the `sig` list, there are several
        *injected* args:
        1. A positional arg `name` of type TargetName is always the first arg.
        2. A keyword arg `deps` of type TargetList and default value `None`
            (or empty list) is always the first after all builder args.
        3. A keyword arg `cachable` of type bool and default value taken from
           the signature registration call (`cachable` arg).
        4. A keyword arg `license` of type StrList and default value [].
        5. A keyword arg `policies` of type StrList and default value [].
        6. A keyword arg `packaging_params` of type dict and default value {}
            (empty dict).
        7. A keyword arg `runtime_params` of type dict and default value {}
            (empty dict).
        8. A keyword arg `build_params` of type dict and default value {}
            (empty dict).
        9. A keyword arg `attempts` of type int and default value 1.
        """
        if self.sig is not None:
            raise KeyError('{} already registered a signature!'
                           .format(builder_name))
        self.sig = OrderedDict(name=ArgSpec(PropType.TargetName, Empty))
        self.docstring = docstring
        kwargs_section = False
        for arg_spec in listify(sig):
            arg_name, sig_spec = evaluate_arg_spec(arg_spec)
            if arg_name in self.sig or arg_name in INJECTED_ARGS:
                raise SyntaxError(
                    "duplicate argument '{}' in function definition"
                    .format(arg_name))
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
        self.sig['deps'] = ArgSpec(PropType.TargetList, None)
        self.sig['cachable'] = ArgSpec(PropType.bool, cachable)
        self.sig['license'] = ArgSpec(PropType.StrList, None)
        self.sig['policies'] = ArgSpec(PropType.StrList, None)
        self.sig['packaging_params'] = ArgSpec(PropType.dict, None)
        self.sig['runtime_params'] = ArgSpec(PropType.dict, None)
        self.sig['build_params'] = ArgSpec(PropType.dict, None)
        self.sig['attempts'] = ArgSpec(PropType.numeric, 1)


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


def register_builder_sig(
        builder_name, sig=None, docstring=None, cachable: bool=True,
        attempts=1):
    Plugin.builders[builder_name].register_sig(
        builder_name, sig, docstring, cachable, attempts)
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


def register_test_func(builder_name):
    def register_decorator(test_func):
        if Plugin.builders[builder_name].test_func:
            raise KeyError('{} already registered a test function!'
                           .format(builder_name))
        Plugin.builders[builder_name].test_func = test_func
        logger.debug('Registered {0} builder signature from '
                     '{1.__module__}.{1.__name__}()', builder_name, test_func)

        @wraps(test_func)
        def tester_wrapper(*args, **kwrags):
            return test_func(*args, **kwrags)
        return tester_wrapper
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
