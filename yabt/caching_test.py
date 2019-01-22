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
yabt caching tests
~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""

import json
from os.path import isdir, isfile, join

import pytest

from .caching import (get_prebuilt_targets, save_target_in_cache,
                      save_test_in_cache)
from .buildcontext import BuildContext
from .graph import populate_targets_graph
from .utils import rmtree


slow = pytest.mark.skipif(not pytest.config.getoption('--with-slow'),
                          reason='need --with-slow option to run')


@slow
@pytest.mark.usefixtures('in_caching_project')
def test_prebuilt_targets_case1(basic_conf):
    """Test pre-built case #1 - all base deps should be marked as pre-built.

    See issue: https://github.com/resonai/ybt/issues/61
    """
    basic_conf.targets = [':builder']
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    pre_built = get_prebuilt_targets(build_context)
    assert set((':build-tools', ':tools', ':unzip', ':ubuntu')) == pre_built
    assert (set((':builder', ':builder-base', ':build-tools',
                 ':tools', ':unzip', ':ubuntu')) ==
            set(build_context.target_graph.nodes))


@slow
@pytest.mark.usefixtures('in_caching_project')
def test_prebuilt_targets_case2(basic_conf):
    """Test pre-built case #2 - nothing should be marked pre-built.

    See issue: https://github.com/resonai/ybt/issues/61
    """
    basic_conf.targets = [':an-image']
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    pre_built = get_prebuilt_targets(build_context)
    assert set() == pre_built
    assert (set((':an-image', ':unzip', ':ubuntu')) ==
            set(build_context.target_graph.nodes))


@slow
@pytest.mark.usefixtures('in_caching_project')
def test_prebuilt_targets_case1(basic_conf):
    """Test pre-built case #3 - unzip & ubuntu should NOT mark as prebuilt.

    See issue: https://github.com/resonai/ybt/issues/61
    """
    basic_conf.targets = [':all-images']
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    pre_built = get_prebuilt_targets(build_context)
    assert set((':build-tools', ':tools')) == pre_built
    assert (set((':all-images', ':an-image', ':builder', ':builder-base',
                 ':build-tools', ':tools', ':unzip', ':ubuntu')) ==
            set(build_context.target_graph.nodes))


@slow
@pytest.mark.usefixtures('in_caching_project')
def test_prebuilt_targets_build_base_image(basic_conf):
    """Test pre-built targets when building base images.

    When `--build-base-images` is specified, all targets should be built,
    regardless of base-image status.
    """
    basic_conf.build_base_images = True
    basic_conf.targets = [':builder']
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    pre_built = get_prebuilt_targets(build_context)
    assert set() == pre_built
    assert (set((':builder', ':builder-base', ':build-tools',
                 ':tools', ':unzip', ':ubuntu')) ==
            set(build_context.target_graph.nodes))


def read_file(fpath, parse_json=False):
    with open(fpath, 'r') as f:
        content = f.read()
    if parse_json:
        return json.loads(content)
    return content


_EXP_UNZIP_JSON = """{
    "buildenv": [],
    "builder_name": "AptPackage",
    "deps": [],
    "flavor": null,
    "name": ":unzip",
    "props": {
        "attempts": 1,
        "build_params": {},
        "license": [],
        "package": "unzip",
        "packaging_params": {},
        "policies": [],
        "repo_key": null,
        "repo_keyserver": "hkp://keyserver.ubuntu.com:80",
        "repository": null,
        "runtime_params": {},
        "version": null
    },
    "tags": [
        "apt-installable"
    ]
}"""


@pytest.mark.usefixtures('in_caching_project')
def test_save_target_to_cache(basic_conf):
    cache_dir = join(basic_conf.project_root, 'yabtwork', '.cache')
    rmtree(cache_dir)
    basic_conf.targets = [':all-images']
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    target_name = ':unzip'
    unzip_target = build_context.targets[target_name]
    unzip_target.summary['build_time'] = 5.432
    save_target_in_cache(unzip_target, build_context)
    target_cache_dir = join(cache_dir, 'targets',
                            unzip_target.hash(build_context))
    assert isdir(target_cache_dir)
    target_json_path = join(target_cache_dir, 'target.json')
    artifacts_json_path = join(target_cache_dir, 'artifacts.json')
    summary_json_path = join(target_cache_dir, 'summary.json')
    assert isfile(target_json_path)
    assert isfile(artifacts_json_path)
    assert isfile(summary_json_path)
    assert _EXP_UNZIP_JSON == read_file(target_json_path)
    assert '{}' == read_file(artifacts_json_path)
    summary = read_file(summary_json_path, True)
    assert set(('accessed', 'artifacts_hash', 'build_time', 'created',
                'name')) == set(summary.keys())
    assert summary['build_time'] == 5.432
    assert summary['name'] == target_name


@pytest.mark.usefixtures('in_caching_project')
def test_save_test_to_cache(basic_conf):
    cache_dir = join(basic_conf.project_root, 'yabtwork', '.cache')
    rmtree(cache_dir)
    basic_conf.targets = [':all-images']
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    target_name = ':unzip'
    unzip_target = build_context.targets[target_name]
    unzip_target.summary['build_time'] = 5.432
    # If there's no test to cache, the caching should always succeed.
    assert save_test_in_cache(unzip_target, build_context)
    unzip_target.tested.update({'some_test': 5.434})
    # Cannot cache a test without first caching the target.
    assert not save_test_in_cache(unzip_target, build_context)
    # If the build was cached first, the test can also be cached.
    save_target_in_cache(unzip_target, build_context)
    assert save_test_in_cache(unzip_target, build_context)
    target_cache_dir = join(cache_dir, 'targets',
                            unzip_target.hash(build_context))
    assert isdir(target_cache_dir)
    target_json_path = join(target_cache_dir, 'target.json')
    artifacts_json_path = join(target_cache_dir, 'artifacts.json')
    summary_json_path = join(target_cache_dir, 'summary.json')
    tested_json_path = join(target_cache_dir, 'tested.json')
    assert isfile(target_json_path)
    assert isfile(artifacts_json_path)
    assert isfile(summary_json_path)
    assert isfile(tested_json_path)
