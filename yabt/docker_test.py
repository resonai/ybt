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
yabt Docker tests
~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import pytest

from subprocess import check_output, PIPE

from .buildcontext import BuildContext
from .graph import populate_targets_graph, topological_sort
from .yabt import cmd_build


slow = pytest.mark.skipif(not pytest.config.getoption('--with-slow'),
                          reason='need --with-slow option to run')


@slow
@pytest.mark.usefixtures('in_simple_project')
def test_run_in_buildenv(basic_conf):
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph()
    result = build_context.run_in_buildenv(
        'app:flask-hello', ['pip', 'freeze'], stdout=PIPE, stderr=PIPE)
    assert 0 == result.returncode
    for package in [
            b'Flask',
            b'itsdangerous',
            b'Jinja2',
            b'MarkupSafe',
            b'Werkzeug',
            ]:
        assert package in result.stdout
    labels = str(check_output(
        ['docker', 'inspect', '--format={{.Config.Labels}}',
         build_context.targets['app:flask-hello'].image_id]))
    assert 'com.ybt.foo:bar' in labels and 'com.ybt.here:there' in labels


@slow
@pytest.mark.usefixtures('in_simple_project')
def test_ybt_bin_generation(basic_conf):
    basic_conf.targets = ['app:flask-app']
    cmd_build(basic_conf)
    with open('ybt_bin/app/flask-app', 'r') as app_ybt_bin:
        assert ('docker run --name my-flask-app -p 5555:5000'
                in app_ybt_bin.read())


@slow
@pytest.mark.usefixtures('in_pkgmgrs_project')
def test_package_managers_install_order(basic_conf):
    basic_conf.targets = [':the-image']
    cmd_build(basic_conf)
    exp_dockerfile = [
        'FROM python:3\n',
        'ARG DEBIAN_FRONTEND=noninteractive\n',
        'USER root\n',
        'ENV FOO="BAR" PATH="${PATH}:/foo/bar:/ham:/spam" TEST="1"\n',
        'RUN apt-get update -y && apt-get install --no-install-recommends -y '
        'apt-transport-https curl wget && rm -rf /var/lib/apt/lists/*\n',
        'COPY packages1 /tmp/install1\n',
        'RUN tar -xf /tmp/install1/node.tar.gz -C /tmp/install1 && '
        'cd /tmp/install1/node && cat install-nodejs.sh | tr -d \'\\r\' | bash'
        ' && cd / && rm -rf /tmp/install1\n',
        'RUN apt-get update -y && apt-get install --no-install-recommends -y '
        'ruby2.3 ruby2.3-dev && rm -rf /var/lib/apt/lists/*\n',
        'COPY requirements_pip_1.txt /usr/src/\n',
        'RUN pip install --no-cache-dir --upgrade pip && '
        'pip install --no-cache-dir -r /usr/src/requirements_pip_1.txt\n',
        'RUN npm install left-pad --global\n',
        'RUN gem install compass\n',
        'COPY requirements_pip_2.txt /usr/src/\n',
        'RUN pip install --no-cache-dir -r /usr/src/requirements_pip_2.txt\n',
        'WORKDIR /usr/src/app\n',
        'USER root\n',
        'CMD ["foo"]\n',
    ]
    with open('yabtwork/flavor__all__/DockerBuilder/the-image_latest/'
              'Dockerfile', 'r') as dockerfile:
        assert exp_dockerfile == dockerfile.readlines()


@slow
@pytest.mark.usefixtures('in_pkgmgrs_project')
def test_generate_needed_lists(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = [':another-image']
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph()
    result = build_context.run_in_buildenv(
        ':another-image', ['ls', '/etc/apt/sources.list.d/'],
        stdout=PIPE, stderr=PIPE)
    assert 0 == result.returncode
    for file in [
            b'another-image.list',
            b'nodesource.list',
            ]:
        assert file in result.stdout
