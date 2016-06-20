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

# pylint: disable=invalid-name, unused-argument

"""
yabt Apt Builders
~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import requests

from ..extend import (
    PropType as PT, register_build_func, register_builder_sig,
    register_manipulate_target_hook)
from ..utils import yprint


LAUNCHPAD_URL = ('https://launchpad.net/api/1.0/'
                 '~{ppa_owner}/+archive/{ppa_name}')
LAUNCHPAD_SOURCE_LINE = ('deb http://ppa.launchpad.net/{ppa_owner}/{ppa_name}/'
                         '{distro_id} {distro_codename} main')
VALID_SOURCE_TYPES = frozenset(('deb',))  # 'deb-src'


register_builder_sig(
    'AptPackage',
    [('package', PT.str),
     ('version', PT.str, None),
     ('repository', PT.str, None),
     ('repo_key', PT.str, None),
     ('repo_keyserver', PT.str, 'hkp://keyserver.ubuntu.com:80'),
     ])


def format_apt_specifier(target):
    if target.props.version:
        return '{0.package}={0.version}'.format(target.props)
    return '{0.package}'.format(target.props)


@register_build_func('AptPackage')
def apt_package_builder(build_context, target):
    yprint(build_context.conf, 'Fetch and cache Apt package', target)


@register_manipulate_target_hook('AptPackage')
def apt_package_manipulate_target(build_context, target):
    target.tags.add('apt-installable')
    if target.props.repository:
        target.tags.add('apt-repository')
        # translate to AptRepository props
        target.props.source = target.props.pop('repository')
        target.props.key = target.props.pop('repo_key')
        target.props.keyserver = target.props.pop('repo_keyserver')


register_builder_sig(
    'AptRepository',
    [('source', PT.str),
     ('key', PT.str, None),
     ('keyserver', PT.str, 'hkp://keyserver.ubuntu.com:80'),
     ])


@register_build_func('AptRepository')
def apt_repository_builder(build_context, target):
    pass


@register_manipulate_target_hook('AptRepository')
def apt_repository_manipulate_target(build_context, target):
    target.tags.add('apt-repository')


def expand_ppa(path: str, distro: dict):
    ppa = path.split(':')[1].split('/')
    ppa_owner = ppa[0]
    ppa_name = ppa[1] if len(ppa) > 0 else 'ppa'
    source_line = LAUNCHPAD_SOURCE_LINE.format(
        ppa_owner=ppa_owner, ppa_name=ppa_name,
        distro_id=distro.get('id', 'ubuntu').lower(),
        distro_codename=distro.get('codename', 'trusty'))
    return source_line, ppa_owner, ppa_name


def parse_apt_repository(build_context, target, distro):
    source_line = target.props.source
    apt_key_cmd = None
    # Parse PPA
    if source_line.startswith('ppa:'):
        source_line, ppa_owner, ppa_name = expand_ppa(source_line, distro)
        response = requests.get(
            LAUNCHPAD_URL.format(ppa_owner=ppa_owner, ppa_name=ppa_name),
            headers={'Accept': 'application/json'})
        if response.status_code != 200:
            raise RuntimeError('Failed getting PPA info for {}'.format(target))
        target.props.key = response.json()['signing_key_fingerprint']
    # Build apt-key command
    if target.props.key:
        apt_key_cmd = ('apt-key adv --keyserver {keyserver} --recv {key}'
                       .format(**target.props))
    # Clean up and validate apt source line
    chunks = source_line.split('#', 1)[0].strip().split()
    if not chunks or chunks[0] not in VALID_SOURCE_TYPES:
        raise ValueError('Invalid source line "{}"'.format(source_line))
    source_line = ' '.join(chunks)
    return source_line, apt_key_cmd
