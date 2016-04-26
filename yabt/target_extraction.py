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
yabt target extraction module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from numbers import Number
from os.path import join, normpath
import types

from ostrich.utils.collections import listify

from .buildfile_utils import to_build_module
from .extend import Builder, Empty, Plugin, PropType as PT
from .logging import make_logger
from .target_utils import norm_name, split_build_module, Target, validate_name
from .utils import norm_proj_path


logger = make_logger(__name__)


def format_num_positional_arguments(builder: Builder):
    min_args = builder.min_positional_args
    max_args = len(builder.sig)
    if min_args < max_args:
        return 'from {} to {} positional arguments'.format(min_args, max_args)
    # TODO(itamar): use inflect()
    return '{} positional argument{}'.format(min_args,
                                             's' if min_args > 1 else '')


def args_to_props(target: Target, builder: Builder, args: list, kwargs: dict):
    """Convert build file `args` and `kwargs` to `target` props.

    Use builder signature to validate builder usage in build-file, raising
    appropriate exceptions on signature-mismatches.

    Use builder signature default values to assign props values to args that
    were not passed in the build-file call.

    This function handles only the arg/kwargs-to-prop assignment, including
    default values when necessary. When it returns, if no exception was raised,
    it is guaranteed that `target.props` contains all args defined in the
    builder registered signature, with values taken either from the build-file
    call, or from default values provided in the signature.

    Specifically, this function DOES NOT do anything about the arg types
    defined in the builder signature.

    :raise TypeError: On signature-call mismatch.
    """
    if len(args) > len(builder.sig):
        # too many positional arguments supplied - say how many we can take
        raise TypeError('{}() takes {}, but {} were given'
                        .format(target.builder_name,
                                format_num_positional_arguments(builder),
                                len(args)))
    # read given args into the matching props according to the signature
    for arg_name, value in zip(builder.sig.keys(), args):
        target.props[arg_name] = value
    # read given kwargs into the named props, asserting matching sig arg names
    for arg_name, value in kwargs.items():
        if arg_name not in builder.sig:
            raise TypeError("{}() got an unexpected keyword argument '{}'"
                            .format(target.builder_name, arg_name))
        if arg_name in target.props:
            raise TypeError("{}() got multiple values for argument '{}'"
                            .format(target.builder_name, arg_name))
        target.props[arg_name] = value
    # go over signature args, assigning default values to anything that wasn't
    # assigned from args / kwargs, making sure no positional args are missing
    missing_args = []
    for arg_name, sig_spec in builder.sig.items():
        if arg_name not in target.props:
            if sig_spec.default == Empty:
                missing_args.append(arg_name)
            else:
                target.props[arg_name] = sig_spec.default
    if missing_args:
        # not enough positional arguments supplied - say which
        # TODO(itamar): match Python's error more closely (last "and "):
        # foo() missing 3 required positional arguments: 'a', 'b', and 'c'
        # TODO(itamar): use inflect
        raise TypeError('{}() missing {} required positional argument{}: {}'
                        .format(target.builder_name, len(missing_args),
                                's' if len(missing_args) > 1 else '',
                                ', '.join("'{}'".format(arg)
                                          for arg in missing_args)))
    logger.debug('Got props for target: {}', target)


def handle_typed_args(target, builder, build_module):

    def assert_type(arg_name, value, class_or_type_or_tuple, type_name):
        if value is None or isinstance(value, class_or_type_or_tuple):
            return value
        raise TypeError('{}: got `{}`, expected {} value'
                        .format(arg_name, value, type_name))

    def handle_target_name(arg_name, value):
        return '{}:{}'.format(
            build_module,
            validate_name(assert_type(arg_name, value, str, 'string')))

    def handle_target_ref(arg_name, value):
        return norm_name(build_module,
                         assert_type(arg_name, value, str, 'string'))

    def handle_file(arg_name, value):
        if assert_type(arg_name, value, str, 'filename') is not None:
            return norm_proj_path(value, build_module)

    for arg_name, value in target.props.items():
        arg_type = builder.sig[arg_name].type
        if arg_type == PT.str:
            assert_type(arg_name, value, str, 'string')
        elif arg_type == PT.numeric:
            assert_type(arg_name, value, Number, 'numeric')
        elif arg_type == PT.list:
            target.props[arg_name] = listify(value)
        elif arg_type == PT.StrList:
            target.props[arg_name] = [
                assert_type(arg_name, val, str, 'string')
                for val in listify(value)]
        elif arg_type == PT.TargetName:
            target.props[arg_name] = handle_target_name(arg_name, value)
        elif arg_type == PT.Target:
            target.props[arg_name] = handle_target_ref(arg_name, value)
        elif arg_type == PT.TargetList:
            target.props[arg_name] = [
                handle_target_ref(arg_name, val) for val in listify(value)]
        elif arg_type == PT.File:
            target.props[arg_name] = handle_file(arg_name, value)
        elif arg_type == PT.FileList:
            target.props[arg_name] = [
                handle_file(arg_name, val) for val in listify(value)]


def extractor(
        builder_name: str, builder: Builder, build_file_path: str,
        build_context) -> types.FunctionType:
    """Return a target extraction function for a specific builder and a
       specific build file."""
    build_module = to_build_module(build_file_path, build_context.conf)

    def extract_target(*args, **kwargs):
        """The actual target extraction function that is executed when any
           builder function is called in a build file."""
        target = Target(builder_name=builder_name)
        # convert args/kwargs to target.props and handle arg types
        args_to_props(target, builder, args, kwargs)
        raw_name = target.props.name
        handle_typed_args(target, builder, build_module)
        logger.debug('Extracting target: {}', target)
        # promote the `name` and `deps` from props to the target instance
        target.name = target.props.pop('name')
        target.deps = target.props.pop('deps', [])
        if target.deps:
            logger.debug('Got deps for target "{0.name}": {0.deps}', target)
        # invoke builder hooks on extracted target
        for hook_name, hook in Plugin.get_hooks_for_builder(builder_name):
            logger.debug('About to invoke hook {} on target {}',
                         hook_name, target)
            hook(build_context, target)
        # save the target in the build context
        build_context.register_target(target)
        logger.debug('Registered {}', target)

    return extract_target
