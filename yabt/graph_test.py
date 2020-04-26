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

import hashlib
import networkx
from networkx.algorithms import dag
import pytest

from . import test_utils as tu
from .test_utils import generate_random_dag
from .buildcontext import BuildContext
from .graph import (
        get_descendants, populate_targets_graph,
        topological_sort, get_graph_roots,
        cut_from_graph
    )


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


@pytest.mark.slow
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


@pytest.mark.slow
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
    assert (
        [':flask', ':gunicorn', 'common:logging',
         'yapi/server:users', 'common:base',
         'fe:fe', 'yapi/server:yapi', 'yapi/server:yapi-gunicorn'
         ] == list(topological_sort(build_context.target_graph)))


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


def calc_node_hash(graph, sort_g_list, node):
    md5 = hashlib.md5()
    md5.update(node.encode('utf8'))
    childs = dag.descendants(graph, node)
    for name in sort_g_list:
        if name in childs:
            md5.update(name.encode('utf8'))
    return md5.hexdigest()


def subgraph_stable_topsort_test(graph):
    """Test that sort is stable for subgraph"""
    def shuffle_graph(graph):
        nodes = list(graph.nodes())
        random.shuffle(nodes)
        new_graph = networkx.DiGraph()
        for name in nodes:
            new_graph.add_node(name)
        edges = list(graph.edges())
        random.shuffle(edges)
        for edge in edges:
            new_graph.add_edge(edge[0], edge[1])
        return new_graph
    top_sort_l = list(topological_sort(graph))
    hash_res0 = dict()
    for root in get_graph_roots(graph):
        hash_res0[root] = calc_node_hash(graph, top_sort_l, root)
    for i in range(5):
        cur_g = shuffle_graph(graph)
        cur_top_sort_l = list(topological_sort(cur_g))
        assert top_sort_l == cur_top_sort_l
    for root in get_graph_roots(graph):
        cur_g = cut_from_graph(graph, root)
        top_sort_l = list(topological_sort(cur_g))
        node_hash = calc_node_hash(cur_g, top_sort_l, root)
        assert hash_res0[root] == node_hash


@pytest.mark.slow
def test_stable_topological_sort1():
    """Using CBuildTrgtTest.create_rand_graph
       to create a random graph
    """
    bldt = tu.CBuildTrgtTest()
    graph = bldt.create_rand_graph()
    subgraph_stable_topsort_test(graph)


def test_stable_topological_sort2():
    """ Using generate_random_dag
         to create a random graph
    """
    graph = tu.generate_random_dag([str(x) for x in range(10)])
    subgraph_stable_topsort_test(graph)


def test_stable_topological_sort3():
    """ On this graph failed stable_reverse_topological_sort"""
    graph = networkx.DiGraph()
    graph.add_edge('A', 'C')
    graph.add_edge('A', 'D')
    graph.add_edge('B', 'E')
    graph.add_edge('B', 'C')
    graph.add_edge('B', 'D')
    subgraph_stable_topsort_test(graph)


def test_stable_topological_sort4():
    """ On this graph failed old failed mod_kahn_top_sort"""
    graph = networkx.DiGraph()
    graph.add_edge('A', 'D')
    graph.add_edge('A', 'E')
    graph.add_edge('B', 'C')
    graph.add_edge('C', 'D')
    subgraph_stable_topsort_test(graph)


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
    assert 'Could not resolve 6 targets' in ex_msg
    assert (':builderz (possible misspelling of [\':builder\']) - ' +
            'buildenv of typo:foo') in ex_msg
    assert ('typo:bar (possible misspelling of [\'typo:base\', \'typo:yapi\'' +
            ', \'typo:flask\']) - seen on command line') in ex_msg
    assert ('typo:blask (possible misspelling of [\'typo:flask\',' +
            ' \'typo:base\', \'typo:yapi\']) - ' +
            'dependency of typo:yapi') in ex_msg
    assert ('typo:loggin (possible misspelling of [\'typo:logging\',' +
            ' \'typo:foo\', \'typo:yapi\']) - ' +
            'dependency of typo:base') in ex_msg
    assert ('typo:xyzxyzxyz (possible misspelling of []) - dependency of ' +
            'typo:unsimilar') in ex_msg
    assert ('typo:zapi (possible misspelling of [\'typo:yapi\', ' +
            '\'typo:base\'' +
            ', \'typo:flask\']) - dependency of typo:foo') in ex_msg
    # # expecting 6 unresolved targets (so error message will have 7 lines)
    assert 7 == len(ex_msg.split('\n'))
