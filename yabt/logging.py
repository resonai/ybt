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
yabt Logging
~~~~~~~~~~~~~~~~~~~~~~~

Implement logger adapter and brace formatter to allow using new-style string
formatting in logging messages, following the logging cookbook:
https://docs.python.org/3.5/howto/logging-cookbook.html#use-of-alternative-formatting-styles

:author: Itamar Ostricher
"""


import logging
import sys


class Message:  # pylint: disable=too-few-public-methods
    """Simple message class for logger adapter."""

    def __init__(self, fmt, args):
        self.fmt = fmt
        self.args = args

    def __str__(self):
        try:
            return self.fmt.format(*self.args)
        except:
            # Sometimes we just want to log something with {}, with no
            # formatting. json for example.
            return self.fmt


class StyleAdapter(logging.LoggerAdapter):
    """A Style logger adapter to allow new-style string formatting in logging.

    Taken from Python logging cookbook:
    https://docs.python.org/3.5/howto/logging-cookbook.html#use-of-alternative-formatting-styles
    """

    def __init__(self, logger, extra=None):
        super().__init__(logger, extra or {})

    def log(self, level, msg, *args, **kwargs):
        if self.isEnabledFor(level):
            msg, kwargs = self.process(msg, kwargs)
            self.logger._log(level, Message(msg, args), (), **kwargs)  # noqa pylint: disable=protected-access


def add_stream_handler(logger, stream):
    """Add a brace-handler stream-handler using `stream` to `logger`."""
    handler = logging.StreamHandler(stream=stream)
    # Using Brace Formatter (see
    # https://docs.python.org/3.5/howto/logging-cookbook.html#use-of-alternative-formatting-styles)
    formatter = logging.Formatter(
        '{asctime} {name:24s} {levelname:8s} {message}', style='{')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def configure_logging(conf):
    """Initialize and configure logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, conf.loglevel.upper()))
    if conf.logtostderr:
        add_stream_handler(root_logger, sys.stderr)
    if conf.logtostdout:
        add_stream_handler(root_logger, sys.stdout)


def make_logger(name: str) -> logging.Logger:
    """Return a sub-logger with name `name`.

    Recommended use in top of using module:
    ```
    logger = logging.make_logger(__name__)
    ```
    """
    return StyleAdapter(logging.getLogger(name))
