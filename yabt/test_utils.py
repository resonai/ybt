# -*- coding: utf-8 -*-

# Copyright 2019 Resonai Ltd. All rights reserved
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
utilities for tests
~~~~~~~~~~~~~~~~~~~~~~~

:author: Dana Shamir
"""
import re
import random
import string
import hashlib
import networkx as nx
from networkx.algorithms import dag
from datetime import datetime


def generate_random_dag(nodes, min_rank=0, max_rank=10, edge_prob=0.3):
    """Return a random DAG with nodes from `nodes`.

    and edges can only go from nodes[i] -> nodes[j] if i < j
    (guaranteeing DAGness).
    """
    g = nx.DiGraph()
    g.add_nodes_from(nodes)
    for j in range(1, len(nodes)):
        rank = random.randint(min_rank, min(j, max_rank))
        g.add_edges_from((nodes[i], nodes[j])
                         for i in random.sample(range(j), k=rank)
                         if random.random() > edge_prob)
    return g


def create_dag_eges(num, p):
    """ Generate a directed acyclic graph
    Parameters
    ----------
    num : int
        The number of nodes.
    p : float
        Probability for edge creation.
    ofname : str
        Name of out dot file
    """
    edges = list()
    for i in range(num):
        for j in range(i+1, num):
            edges.append((i, j))
    e_num = num * (num - 1) // 2
    e_num = min(e_num, int(e_num * p))
    num = len(edges)
    while num > e_num:
        num = num - 1
        edges.remove(edges[random.randint(0, num)])
    return edges


sort_test_cfg = [
    {
        "BuildTargets": [
            {
                "Name": "AptPackage", "Childs": ["AptPackage"], "MinChilds": 0
            },
            {
                "Name": "CppGTest", "Childs": ["CppLib", "CppProg"],
                "MinChilds": 1
            },
            {
                "Name": "CppLib", "Childs": ["Proto", "AptPackage"],
                "MinChilds": 1
            },
            {
                "Name": "CppProg", "Childs": ["CppLib", "Proto", "AptPackage"],
                "MinChilds": 1
            },
            {
                "Name": "CustomInstaller", "Childs":
                [
                    "CppLib", "Proto", "CppProg", "CppGTest",
                    "Python", "PythonPackage", "PythonTest"
                ], "MinChilds": 3
            },
            {
                "Name": "Proto", "Childs": ["Proto"], "MinChilds": 0
            },
            {
                "Name": "Python", "Childs": ["Python", "PythonPackage"],
                "MinChilds": 0
            },
            {
                "Name": "PythonPackage", "Childs": ["PythonPackage"],
                "MinChilds": 0
            },
            {
                "Name": "PythonTest", "Childs": ["PythonPackage", "Python"],
                "MinChilds": 2
            }
        ]
    },
    {
        "Config": {
            "MinNameLen": 2, "MaxNameLen": 5, "Steps": 100, "MaxStepNodes": 8
        }
    }
]


class CBuildTrgtTest:
    """Class for creating a random package
        with projects and their dependencies"""
    class CBuildTrgtType:
        """ Type of project"""
        def __init__(self, trg):
            self.name = trg['Name']
            self.childs = trg['Childs']  # Types of available dependencies
            self.min_childs = trg['MinChilds']  # Minimum of dependencies

        def is_child(self, trg):
            return trg.name in self.childs

    def __init__(self):
        bd_trgs = sort_test_cfg[0]['BuildTargets']
        self.trgs = list()
        for trg in bd_trgs:
            self.trgs.append(CBuildTrgtTest.CBuildTrgtType(trg))
        cfg = sort_test_cfg[1]['Config']
        self.min_name_len = cfg['MinNameLen']
        self.max_name_len = cfg['MaxNameLen']
        self.steps = cfg['Steps']
        self.max_step_nodes = cfg['MaxStepNodes']
        self.letters = string.ascii_lowercase

    def __new_build_trgt(self):
        """Generate a random string """
        str_len = random.randint(self.min_name_len, self.max_name_len)
        name = ''.join(random.choice(self.letters) for i in range(str_len))
        i = random.randint(0, len(self.trgs) - 1)
        return [name, self.trgs[i]]

    def __add_node(self, nx_g, name, b_type_name):
        """ Added node with its type"""
        for trg in self.trgs:
            if trg.name == b_type_name:
                nx_g.add_node(name, trg=trg)
                return

    def __add_nodes(self, nx_g):
        """ Added random nodes with its random dependencies"""
        d_t = dict()
        i_n = random.randint(1, self.max_step_nodes)
        for _ in range(i_n):
            trg = self.__new_build_trgt()
            d_t.update({trg[0]: trg[1]})
        l_g = list(nx_g)
        l_d = nx.get_node_attributes(nx_g, 'trg')
        l_n = len(l_g)
        for name in d_t:
            if name not in nx_g:
                trg = d_t[name]
                childs = 0
                if l_n > 0:
                    r_n = random.randint(0, l_n - 1)
                    for i in range(0, r_n):
                        child_name = l_g[i]
                        child_trg = l_d[child_name]
                        if trg.is_child(child_trg):
                            nx_g.add_edge(name, child_name)
                            childs = childs + 1
                if trg.min_childs <= childs:
                    nx_g.add_node(name, trg=trg)
                elif childs > 0:
                    nx_g.remove_node(name)

    def create_rand_graph(self):
        """ Created string random DAG """
        nx_g = nx.DiGraph()
        for _ in range(self.steps):
            self.__add_nodes(nx_g)
        return nx_g


def calc_node_hash(graph, sort_g_list, node):
    md5 = hashlib.md5()
    md5.update(node.encode('utf8'))
    childs = dag.descendants(graph, node)
    for name in sort_g_list:
        if name in childs:
            md5.update(name.encode('utf8'))
    return md5.hexdigest()


def write_test_dot(nx_g, out_fname=''):
    """Write build graph in dot format to `out_f` file-like object."""
    if not out_fname:
        now = datetime.now()
        out_fname = now.strftime('ybt_%2d_%2m_%Y_%2H_%2M_%2S_%f.dot')
    fout = open(out_fname, 'w')
    fout.write('strict digraph    {\n')
    clrs = nx.get_node_attributes(nx_g, 'color')
    stls = nx.get_node_attributes(nx_g, 'style')
    fclrs = nx.get_node_attributes(nx_g, 'fillcolor')
    for node in nx_g.nodes():
        s = '['
        if node in clrs:
            s = s + 'color=' + str(clrs[node]) + ','
        if node in stls:
            s = s + 'color=' + str(stls[node]) + ','
        if node in fclrs:
            s = s + 'color=' + str(fclrs[node]) + ','
        fout.write('  {} {}];\n'.format(node, s))
    fout.writelines('    {} -> {};\n'.format(u, v)
                    for u, v in nx_g.edges())
    fout.write('}\n\n')
    fout.close()
    print('Output file is "{}"'.format(out_fname))
    return out_fname


def dot_file_line_proc(nx_g, line):
    """ Parsing dot file line """
    edge = re.split(r'\s*->\s*', line)
    if len(edge) == 2:
        name = re.sub(r'\s+|;', '', edge[0]).strip('\"')
        child_name = re.sub(r'\s+|;', '', edge[1]).strip('\"')
        nx_g.add_edge(name, child_name)
    else:
        temp = re.split(r'\s+', line, 2)
        if (not temp[0]) & bool(temp[1]):
            name = temp[1].strip('\"')
            attributes = dict()
            for attr_str in re.split(r'\[|,|\]|;|\n', temp[2]):
                attr = re.split('=', attr_str)
                if len(attr) == 2:
                    attributes.update({
                        attr[0].strip('\"'): attr[1].strip('\"')})
            nx_g.add_node(name, **attributes)


def load_dot(in_fname):
    """ Read graph from dot format """
    with open(in_fname, 'r') as in_f:
        nx_g = nx.DiGraph()
        for line in in_f:
            dot_file_line_proc(nx_g, line)
    return nx_g
