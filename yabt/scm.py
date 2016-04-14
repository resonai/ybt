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
yabt source control subsystem
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import pkg_resources

from .logging import make_logger


logger = make_logger(__name__)


class SourceControl:
    """Source Control subsystem"""

    providers = {}

    @classmethod
    def load_provider(cls, scm_name: str):
        """Load and return named SCM provider class.

        :raises KeyError: If no SCM provider which name `scm_name` registered.
        """
        for entry_point in pkg_resources.iter_entry_points('yabt.scm',
                                                           scm_name):
            entry_point.load()
            logger.debug('Loaded SCM provider {0.name} from {0.module_name} '
                         '(dist {0.dist})', entry_point)
        logger.debug('Loaded {} SCM providers', len(cls.providers))
        if scm_name not in cls.providers:
            raise KeyError('Unknown SCM identifier {}'.format(scm_name))
        return cls.providers[scm_name]

    def __init__(self, conf):
        """
        :param conf: A yabt.config.Config object.
        """
        self.conf = conf

    def get_revision(self) -> str:
        """Return revision string of active repo tip / head."""
        raise NotImplementedError('Implement in concrete SCM provider')


def register_scm_provider(scm_name: str):
    """Return a decorator for registering a SCM provider named `scn_name`."""

    def register_decorator(scm_class: SourceControl):
        """Decorator for registering SCM provider."""
        if scm_name in SourceControl.providers:
            raise KeyError('{} already registered!'.format(scm_name))
        SourceControl.providers[scm_name] = scm_class
        logger.debug('Registered {0} SCM from {1.__module__}.{1.__name__}',
                     scm_name, scm_class)
        return scm_class
    return register_decorator


@register_scm_provider('none')
class NoSCM(SourceControl):
    """Default trivial (AKA non-existent) concrete SCM implementation."""

    def get_revision(self):
        raise NotImplementedError('NoSCM')
