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
yabt Build File parser
~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import os
import sys
import traceback

import colorama

from .config import Config
from .glob import glob
from .logging import make_logger
from .scm import SourceControl


logger = make_logger(__name__)


def err(msg, *args, **kwargs):
    print(msg.format(*args, **kwargs), file=sys.stderr)


def report_buildfile_error(buildfile_path, unused_conf: Config):
    exc_type, exc, tb = sys.exc_info()
    stack = traceback.extract_tb(tb)
    if len(stack) > 1:
        err('Traceback (most recent call first):')
        for fname, line, unused_func, text in reversed(stack):
            err('  File "{}", line {}',
                buildfile_path if fname == '<string>' else fname, line)
            if text:
                err('    {}', text)
            if fname == '<string>':
                break
    print(colorama.Fore.RED, file=sys.stderr, end='')
    if exc_type == SyntaxError:
        err('Fatal: Syntax error in build file {}, line {}:\n  {}\n  {: >{}}',
            buildfile_path, exc.lineno,
            # TODO(itamar): Fix issue with empty exc.text
            # (occurs when keyword arg repeats in call to build func)
            exc.text.strip('\n') if exc.text else '', '^', exc.offset)
    else:
        err('Fatal: {}', exc)
    print(colorama.Style.RESET_ALL, file=sys.stderr, end='')
    sys.exit(1)


def process_build_file(buildfile_path: str, build_context, conf: Config):
    # TODO(itamar): Write tests that verify that this is really not needed in
    # any scenario... (caused issue when referring to target in yroot using
    # `.:foo` syntax from yroot, but normalizing the target name seemed to
    # resolve this). (test also `@` variants etc.)

    # abs_path = os.path.abspath(buildfile_path)
    if buildfile_path in build_context.processed_build_files:
        logger.debug('Skipping processed build file {}', buildfile_path)
        return
    build_context.processed_build_files.add(buildfile_path)
    logger.info('Processing build file {}', buildfile_path)

    with open(buildfile_path, 'r') as buildfile:
        global_context = globals()
        global_context.update({
            'conf': conf,
            'SCM': conf.scm,
            'Glob': glob,
        })
        curdir = os.getcwd()
        try:
            os.chdir(os.path.dirname(buildfile_path))
            # pylint: disable=exec-used
            exec(buildfile.read(), global_context,
                 build_context.get_target_extraction_context(buildfile_path))
        except:
            report_buildfile_error(buildfile_path, conf)
        finally:
            os.chdir(curdir)
