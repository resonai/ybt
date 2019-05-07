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
yabt target graph tests
~~~~~~~~~~~~~~~~~~~~~~~

:author: Itamar Ostricher
"""


from concurrent.futures import ThreadPoolExecutor
from functools import reduce
import random
from unittest.mock import Mock

import networkx
import pytest

from .test_utils import generate_random_dag
from .buildcontext import BuildContext
from .graph import (get_descendants, populate_targets_graph, topological_sort)


slow = pytest.mark.skipif(not pytest.config.getoption('--with-slow'),
                          reason='need --with-slow option to run')


def make_random_dag_build_context(
        num_nodes, min_rank=0, max_rank=10, edge_prob=0.3):
    """Return a build context based on a random DAG with `num_nodes` nodes."""

    class DummyTarget():
        def __init__(self, n):
            self.name = n
            self.value = n

    # Use random DAG to create a build context with dummy targets
    g = generate_random_dag(list(range(num_nodes)),
                            min_rank, max_rank, edge_prob)
    build_context = BuildContext(Mock())
    build_context.target_graph = g
    for n in g.nodes():
        build_context.targets[n] = DummyTarget(n)

    return g, build_context


def random_dag_scan(num_nodes):
    """Test that `target_iter` generates nodes in a correct order"""
    g, build_context = make_random_dag_build_context(num_nodes)
    # for every generated node, assert that all the prerequisite nodes are
    # already in the `done` set
    done = set()
    for target in build_context.target_iter():
        assert done.issuperset(get_descendants(g, target.name))
        target.done()
        done.add(target.name)
    # also assert that at the end, all nodes are "done"
    assert done == set(g.nodes())


def test_small_dag_scan():
    random_dag_scan(500)


@slow
def test_big_dag_scan():
    random_dag_scan(2000)


def multithreaded_dag_scanner(num_nodes, num_threads=16):
    """Test that a multi-threaded `target_iter` with `num_nodes` nodes and
       `num_threads` threads generates nodes in the correct order, by
       comparing reduce-friendly operations between the multi-threaded method
       and a topological-sort-based single-threaded method.
    """

    g, build_context = make_random_dag_build_context(num_nodes)
    # set leaf nodes values to random (-3,3) numbers,
    # and non-leaf nodes to "No value" (None)
    for n, out_deg in g.out_degree():
        build_context.targets[n].value = (random.randint(-3, 3)
                                          if out_deg == 0 else None)

    def func(target, values):
        """Reducer-friendly operator"""
        deps = list(g.successors(target.name))
        for dep in deps:
            assert values[dep] is not None
        if len(deps) == 0:
            # a leaf - just copy the value
            values[target.name] = target.value
        else:
            assert values[target.name] is None
            if len(deps) == 1:
                # node with one dependency - use dep value + 1
                values[target.name] = values[deps[0]] + 1
            else:
                # multi-dep node - apply reducer to dep values
                # reducer either sum or mult, depending on node parity
                reducer = ((lambda x, y: x + y) if target.name & 1
                           else (lambda x, y: x * y))
                values[target.name] = reduce(
                    reducer, (values[dep] for dep in deps))

    # Scan DAG in topological sort order, applying operator in order
    topo_vals = [None] * num_nodes
    for i in reversed(range(num_nodes)):
        func(build_context.targets[i], topo_vals)

    # Multi-threaded DAG scan using ready-queue
    queue_vals = [None] * num_nodes
    with ThreadPoolExecutor(max_workers=num_threads) as executor:

        def do_func(node):
            func(node, queue_vals)
            node.done()

        executor.map(do_func, build_context.target_iter())

    # Compare single vs. multi threaded results
    for topo_val, q_val in zip(topo_vals, queue_vals):
        assert topo_val is not None and q_val is not None
        assert topo_val == q_val


def test_small_multithreaded_dag_scan():
    multithreaded_dag_scanner(1000)


@slow
def test_big_multithreaded_dag_scan():
    multithreaded_dag_scanner(10000)


@pytest.mark.usefixtures('in_dag_project')
def test_target_graph(basic_conf):
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    assert (
        set(('yapi/server:users', ':flask', ':gunicorn', 'common:logging',
             'fe:fe', 'yapi/server:yapi', 'yapi/server:yapi-gunicorn',
             'common:base')) == set(build_context.target_graph.nodes))
    assert (
        set((('fe:fe', 'yapi/server:users'), ('fe:fe', ':flask'),
             ('fe:fe', 'common:base'), ('yapi/server:yapi', ':flask'),
             ('yapi/server:yapi', 'common:base'),
             ('yapi/server:yapi-gunicorn', 'yapi/server:yapi'),
             ('yapi/server:yapi-gunicorn', 'common:base'),
             ('yapi/server:yapi-gunicorn', ':gunicorn'),
             ('common:base', 'common:logging'))) ==
        set(build_context.target_graph.edges))
    assert ([':flask', ':gunicorn', 'common:logging', 'common:base',
             'yapi/server:users', 'fe:fe', 'yapi/server:yapi',
             'yapi/server:yapi-gunicorn'] ==
            list(topological_sort(build_context.target_graph)))


@pytest.mark.usefixtures('in_yapi_dir')
def test_target_graph_worldglob(basic_conf):
    """Test that building a graph with the world-glob specifier works."""
    basic_conf.targets = ['**:*']
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    assert (
        set(('yapi/server:users', ':flask', ':gunicorn', 'common:logging',
             'fe:fe', 'yapi/server:yapi', 'yapi/server:yapi-gunicorn',
             'common:base')) == set(build_context.target_graph.nodes))
    assert (
        set((('fe:fe', 'yapi/server:users'), ('fe:fe', ':flask'),
             ('fe:fe', 'common:base'), ('yapi/server:yapi', ':flask'),
             ('yapi/server:yapi', 'common:base'),
             ('yapi/server:yapi-gunicorn', 'yapi/server:yapi'),
             ('yapi/server:yapi-gunicorn', 'common:base'),
             ('yapi/server:yapi-gunicorn', ':gunicorn'),
             ('common:base', 'common:logging'))) ==
        set(build_context.target_graph.edges))


@pytest.mark.usefixtures('in_yapi_dir')
def test_target_graph_intenral_dir(basic_conf):
    """Test that building graph from internal dir works as expected."""
    basic_conf.targets = ['server']
    build_context = BuildContext(basic_conf)
    populate_targets_graph(build_context, basic_conf)
    assert (
        set(('yapi/server:users', ':flask', ':gunicorn', 'common:logging',
             'yapi/server:yapi', 'yapi/server:yapi-gunicorn',
             'common:base')) == set(build_context.target_graph.nodes))
    assert (
        set((('yapi/server:yapi', ':flask'),
             ('yapi/server:yapi', 'common:base'),
             ('yapi/server:yapi-gunicorn', 'yapi/server:yapi'),
             ('yapi/server:yapi-gunicorn', 'common:base'),
             ('yapi/server:yapi-gunicorn', ':gunicorn'),
             ('common:base', 'common:logging'))) ==
        set(build_context.target_graph.edges))


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


@pytest.mark.usefixtures('in_error_project')
def test_graph_cycles(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['cycle']
    with pytest.raises(RuntimeError) as excinfo:
        populate_targets_graph(build_context, basic_conf)
    ex_msg = str(excinfo.value)
    assert 'Detected cycles in build graph!' in ex_msg
    # expecting 3 cycles (so error message will have 4 lines)
    assert 4 == len(ex_msg.split('\n'))


@pytest.mark.usefixtures('in_error_project')
def test_dep_name_typo(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['typo', 'typo:bar']
    with pytest.raises(ValueError) as excinfo:
        populate_targets_graph(build_context, basic_conf)
    ex_msg = str(excinfo.value)
    assert 'Could not resolve 5 targets' in ex_msg
    assert ':builderz - buildenv of typo:foo' in ex_msg
    assert 'typo:bar - seen on command line' in ex_msg
    assert 'typo:blask - dependency of typo:yapi' in ex_msg
    assert 'typo:loggin - dependency of typo:base' in ex_msg
    assert 'typo:zapi - dependency of typo:foo' in ex_msg
    # # expecting 5 unresolved targets (so error message will have 6 lines)
    assert 6 == len(ex_msg.split('\n'))
