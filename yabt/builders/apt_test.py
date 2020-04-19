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
yabt Apt builder tests
~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import pytest

from . import apt
from ..pkgmgmt import parse_apt_repository
from ..target_utils import Target


DISTRO = {
    'id': 'Ubuntu',
    'release': '14.04',
    'codename': 'trusty',
    'description': 'Ubuntu 14.04.4 LTS',
}


def test_apt_repository_simple_line():
    target = Target('AptRepository')
    llvm_repo = ('deb http://llvm.org/apt/trusty/ '
                 'llvm-toolchain-trusty-3.8 main')
    target.props.source = llvm_repo
    target.props.key = None
    target.props.keyserver = 'hkp://keyserver.ubuntu.com:80'
    source_line, apt_key_cmd = parse_apt_repository(None, target, DISTRO)
    assert llvm_repo == source_line
    assert apt_key_cmd is None


@pytest.mark.slow
def test_apt_repository_ppa_with_key():
    target = Target('AptRepository')
    target.props.source = 'ppa:brightbox/ruby-ng'
    target.props.key = None
    target.props.keyserver = 'hkp://keyserver.ubuntu.com:80'
    source_line, apt_key_cmd = parse_apt_repository(None, target, DISTRO)
    exp_ruby_ng_repo = ('deb http://ppa.launchpad.net/brightbox/ruby-ng/'
                        'ubuntu trusty main')
    exp_ruby_ng_key_cmd = (
        'apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 '
        '--recv 80F70E11F0F0D5F10CB20E62F5DA5F09C3173AA6')
    assert exp_ruby_ng_repo == source_line
    assert exp_ruby_ng_key_cmd == apt_key_cmd
