# -*- coding: utf-8 -*-

"""
yabt Buildfile processing
~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2016 Yowza by Itamar Ostricher
:license: MIT, see LICENSE for more details.
"""


import sys
import traceback

import colorama

from .buildcontext import BuildContext
from .config import Config


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
        err('Syntax Error in build file {}, line {}:\n  {}\n  {: >{}}',
            buildfile_path, exc.lineno, exc.text.strip('\n'), '^', exc.offset)
    else:
        err('YABT Error: {}', exc)
    print(colorama.Style.RESET_ALL, file=sys.stderr, end='')
    sys.exit(1)


def process_build_file(buildfile_path: str, conf: Config):
    # TODO(itamar): Write tests that verify that this is really not needed in
    # any scenario... (caused issue when referring to target in yroot using
    # `.:foo` syntax from yroot, but normalizing the target name seemed to
    # resolve this). (test also `@` variants etc.)

    # abs_path = os.path.abspath(buildfile_path)
    # if abs_path in BuildContext.processed_build_files:
    #   print('Skipping processed build file {}'.format(buildfile_path))
    #   return
    # BuildContext.processed_build_files.add(abs_path)

    with open(buildfile_path, 'r') as buildfile:
        # yglbl = globals()
        # ylcls = locals()
        build_context = BuildContext(conf, buildfile_path)
        global_context = globals()
        # global_context['workdir'] = buildfile_path
        try:
            # pylint: disable=exec-used
            exec(buildfile.read(), global_context,
                 build_context.get_target_extraction_context())
        except:
            report_buildfile_error(buildfile_path, conf)
