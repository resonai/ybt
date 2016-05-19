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
yabt target graph tests
~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


import networkx
import pytest

from .buildcontext import BuildContext
from .graph import populate_targets_graph, topological_sort
from .extend import Plugin


@pytest.mark.usefixtures('in_dag_project')
def test_target_graph(basic_conf):
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    assert (
        set(['yapi/server:users', ':flask', ':gunicorn', 'common:logging',
             'fe:fe', 'yapi/server:yapi', 'yapi/server:yapi-gunicorn',
             'common:base']) == set(build_context.target_graph.nodes()))
    assert (
        set([('fe:fe', 'yapi/server:users'), ('fe:fe', ':flask'),
             ('fe:fe', 'common:base'), ('yapi/server:yapi', ':flask'),
             ('yapi/server:yapi', 'common:base'),
             ('yapi/server:yapi-gunicorn', 'yapi/server:yapi'),
             ('yapi/server:yapi-gunicorn', 'common:base'),
             ('yapi/server:yapi-gunicorn', ':gunicorn'),
             ('common:base', 'common:logging')]) ==
        set(build_context.target_graph.edges()))
    # Can't assert the list directly, because it is not stable / deterministic
    topo_sort = list(topological_sort(build_context.target_graph))

    def assert_dep_chain(*chain):
        dep_chain = [topo_sort.index(target_name) for target_name in chain]
        assert dep_chain == sorted(dep_chain)

    assert_dep_chain('common:logging', 'common:base',
                     'yapi/server:yapi', 'yapi/server:yapi-gunicorn')
    assert_dep_chain(':flask', 'yapi/server:yapi')
    assert_dep_chain(':gunicorn', 'yapi/server:yapi-gunicorn')
    assert_dep_chain(':flask', 'fe:fe')
    assert_dep_chain('yapi/server:users', 'fe:fe')
    assert_dep_chain('common:logging', 'common:base', 'fe:fe')


def test_stable_topological_sort():
    """Test that my modified topological sort is stable.

    Note - not doing many cycles because I saw that even with the non-stable
    implementation, it is stable in the context of the same process...
    (only reruns showed the unstable behavior)
    """
    expected_order = ['world', 'bar', 'baz', 'hello', 'foo']

    graph = networkx.DiGraph()
    graph.add_edges_from([('foo', 'bar'), ('foo', 'baz'),
                          ('bar', 'world'), ('foo', 'hello')])
    assert list(topological_sort(graph)) == expected_order

    same_graph = networkx.DiGraph({'foo': ['baz', 'hello', 'bar']})
    same_graph.add_edge('bar', 'world')
    assert list(topological_sort(same_graph)) == expected_order


def test_topological_sort1():
    graph = networkx.DiGraph()
    graph.add_edges_from([(1, 2), (1, 3), (2, 3)])
    assert list(topological_sort(graph)) == [3, 2, 1]

    graph.add_edge(3, 2)
    with pytest.raises(networkx.NetworkXUnfeasible):
        list(topological_sort(graph))

    graph.remove_edge(2, 3)
    assert list(topological_sort(graph)) == [2, 3, 1]


def test_topological_sort2():
    graph = networkx.DiGraph({1: [2], 2: [3], 3: [4],
                              4: [5], 5: [1], 11: [12],
                              12: [13], 13: [14], 14: [15]})

    with pytest.raises(networkx.NetworkXUnfeasible):
        list(topological_sort(graph))

    graph.remove_edge(1, 2)
    assert list(topological_sort(graph)) == [1, 5, 4, 3, 2, 15, 14, 13, 12, 11]


def test_topological_sort4():
    graph = networkx.Graph()
    graph.add_edge(1, 2)
    with pytest.raises(networkx.NetworkXError):
        list(topological_sort(graph))


def test_topological_sort4():
    graph = networkx.DiGraph()
    graph.add_edge(1, 2)
    assert list(topological_sort(graph)) == [2, 1]
