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
yabt source control subsystem
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import os
import sys

import git

from ..config import Config
from ..logging import make_logger
from ..scm import register_scm_provider
from ..utils import search_for_parent_dir


logger = make_logger(__name__)


@register_scm_provider('git')
class GitSCM:
    """Git SCM implementation."""

    def __init__(self, conf: Config):
        self.repo_dir = search_for_parent_dir(conf.project_root,
                                              with_dirs=set(['.git']))
        if not self.repo_dir:
            print('fatal: "git" scm-provider option given, but not a git '
                  'repository (or any of the parent directories): .git')
            sys.exit(1)
        self._repo = git.Repo(self.repo_dir)
        logger.debug('Initialized Git Repo object at {}', self.repo_dir)
        self.revision = None

    def get_revision(self):
        """Return Git hash of HEAD commit of active repository."""
        if self.revision:
            return self.revision

        if 'GIT_COMMIT' in os.environ:
            self.revision = os.environ['GIT_COMMIT']
        else:
            self.revision = self._repo.head.commit.hexsha
        return self.revision
