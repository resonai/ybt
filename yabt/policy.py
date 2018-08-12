# -*- coding: utf-8 -*-

# Copyright 2018 Resonai Ltd. All rights reserved
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
yabt Policy module
~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""

import json
from os import makedirs
from os.path import isdir, isfile, join, relpath, split
import shutil
from time import time

from ostrich.utils.text import get_safe_path

from .artifact import ArtifactType as AT
from .config import Config
from .docker import get_image_name, handle_build_cache, tag_docker_image
from .graph import get_descendants
from .logging import make_logger
from .target_utils import ImageCachingBehavior, Target
from .utils import hash_tree, rmnode, rmtree


logger = make_logger(__name__)


# source: https://opensource.org/licenses/alphabetical
KNOWN_LICENSES = frozenset((
    '0BSD',
    'AAL',
    'AFL-3.0',
    'AGPL-3.0',
    'APL-1.0',
    'APSL-2.0',
    'Apache-2.0',
    'Artistic-2.0',
    'BSD-2-Clause',
    'BSD-2-Clause-Patent',
    'BSD-3-Clause',
    'BSL-1.0',
    'CATOSL-1.1',
    'CDDL-1.0',
    'CECILL-2.1',
    'CNRI portion of Python License',
    'CNRI-Python',
    'CPAL-1.0',
    'CUA-OPL-1.0',
    'ECL-2.0',
    'EFL-2.0',
    'EPL-1.0',
    'EPL-2.0',
    'EUDatagrid',
    'EUPL-1.1',
    'Entessa',
    'Fair',
    'Frameworx-1.0',
    'GPL-2.0',
    'GPL-3.0',
    'HPND',
    'IPA',
    'IPL-1.0',
    'ISC',
    'LGPL-2.1',
    'LGPL-3.0',
    'LPL-1.02',
    'LPPL-1.3c',
    'LiLiQ-P',
    'LiLiQ-R',
    'LiLiQ-R+',
    'MIT',
    'MPL-1.0',
    'MPL-1.1',
    'MPL-2.0',
    'MS-PL',
    'MS-RL',
    'MirOS',
    'Motosoto',
    'Multics',
    'NASA-1.3',
    'NCSA',
    'NGPL',
    'NPOSL-3.0',
    'NTP',
    'Naumen',
    'Nokia',
    'OCLC-2.0',
    'OFL-1.1',
    'OGTSL',
    'OSL-3.0',
    'PHP-3.0',
    'PostgreSQL',
    'Python-2.0',
    'QPL-1.0',
    'RPL-1.5',
    'RPSL-1.0',
    'RSCPL',
    'SPL-1.0',
    'SimPL-2.0',
    'Sleepycat',
    'UPL',
    'VSL-1.0',
    'W3C',
    'WXwindows',
    'Watcom-1.0',
    'Xnet',
    'ZPL-2.0',
    'Zlib',
    # *** manual additions *** #
    'Other',
    'Commercial',
))


def standard_licenses_only(build_context, target) -> str:
    """A policy function for allowing specifying only known licenses.

    Return error message (string) if policy for `target` is violated,
    otherwise return `None`.

    To apply in project, include this function in the ilst returned by the
    `get_policies` function implemented in the project `YSettings` file.

    See example in tests/errors.
    """
    for license_name in target.props.license:
        if license_name not in KNOWN_LICENSES:
            # TODO: include suggestion for similar known license
            return 'Unknown license: {}'.format(license_name)
    return None


def whitelist_licenses_policy(policy_name: str, allowed_licenses: set):
    """A policy factory for making license-based whitelist policies.

    To apply in project, include the function returned from this factory
    in the ilst returned by the `get_policies` function implemented in the
    project `YSettings` file.

    The factory returns a policy function named
    `whitelist_{policy_name}_licenses` that applies to targets with
    `policy_name` in their policies list.
    The returned policy asserts that all licenses contained in the target
    (including through explicit & implicit dependencies) are in the whitelist
    defined by `allowed_licenses`.

    See example in tests/errors.
    """

    def policy_func(build_context, target):
        """whitelist_{policy_name}_licenses policy function.

        Return error message (string) if policy for `target` is violated,
        otherwise return `None`.
        """
        if policy_name in target.props.policies:
            licenses = set(target.props.license)
            for dep in build_context.generate_all_deps(target):
                licenses.update(dep.props.license)
            licenses.difference_update(allowed_licenses)
            if licenses:
                return 'Invalid licenses for {} policy: {}'.format(
                    policy_name, ', '.join(sorted(licenses)))
        return None

    policy_func.__name__ = 'whitelist_{}_licenses'.format(policy_name)
    return policy_func
