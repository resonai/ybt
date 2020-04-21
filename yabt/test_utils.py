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
import networkx as nx
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


class CBuildTrgtTest:
    """Class for creating a random package
        with projects and their dependencies.

        The package contains several projects. All projects consist of files.
        Single-file projects are also allowed. Some projects may be
        independent of others, some should depend on others, such as
        an installation script. Not all dependencies are valid, for example,
        the library cannot depend on the executable file. All applicable rules
        and dependencies were originally read from a json file. Then I
        hard-coded the contents of the most successful file into sort_test_cfg.
            The CBuildTrgtType class contains the name and properties of the
        project type. In the constructor of the CBuildTrgtTest class, all
        project types are written to the trgs variable and configuration data
        to the min_name_len, max_name_len, steps, max_step_nodes
        variables. File names will be randomly generated from
        min_name_len to max_name_len in length.
            A random package is created in the create_rand_graph function.
        In the loop, we call the __add_nodes function steps times.
        The __add_nodes function adds a maximum of MaxStepNodes
        files. Each file is added along with its random dependencies in
        accordance with the rules from the trgs table. Since files without
        parents are added at each step, the cycle cannot be formed
        on a common graph. Thus, the create_rand_graph function
        always returns a Directed Acyclic Graph (DAG)
    """
    sort_test_cfg = [
        {
            "BuildTargets": [
                {
                    "Name": "AptPackage", "Childs": ["AptPackage"],
                    "MinChilds": 0
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
                    "Name": "CppProg",
                    "Childs": ["CppLib", "Proto", "AptPackage"],
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
                    "Name": "PythonTest",
                    "Childs": ["PythonPackage", "Python"],
                    "MinChilds": 2
                }
            ]
        },
        {
            "Config": {
                "MinNameLen": 2, "MaxNameLen": 5,
                "Steps": 100, "MaxStepNodes": 8
            }
        }
    ]

    class CBuildTrgtType:
        """ Type of project"""
        def __init__(self, trg):
            self.name = trg['Name']
            self.childs = trg['Childs']  # Types of available dependencies
            self.min_childs = trg['MinChilds']  # Minimum of dependencies

        def is_child(self, trg):
            return trg.name in self.childs

    def __init__(self):
        bd_trgs = CBuildTrgtTest.sort_test_cfg[0]['BuildTargets']
        self.trgs = list()
        for trg in bd_trgs:
            self.trgs.append(CBuildTrgtTest.CBuildTrgtType(trg))
        cfg = CBuildTrgtTest.sort_test_cfg[1]['Config']
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

    def __add_nodes(self, graph):
        """ Added random nodes with its random dependencies"""
        edges = dict()
        nod_num = random.randint(1, self.max_step_nodes)
        for _ in range(nod_num):
            trg = self.__new_build_trgt()
            edges.update({trg[0]: trg[1]})
        nodes = list(graph)
        trg_attrs = nx.get_node_attributes(graph, 'trg')
        nodes_len = len(nodes)
        for name in edges:
            if name not in graph:
                trg = edges[name]
                childs = 0
                if nodes_len > 0:
                    child_num = random.randint(0, nodes_len - 1)
                    for i in range(0, child_num):
                        child_name = nodes[i]
                        child_trg = trg_attrs[child_name]
                        if trg.is_child(child_trg):
                            graph.add_edge(name, child_name)
                            childs = childs + 1
                if trg.min_childs <= childs:
                    graph.add_node(name, trg=trg)
                elif childs > 0:
                    graph.remove_node(name)

    def create_rand_graph(self):
        """ Created string random DAG """
        graph = nx.DiGraph()
        for _ in range(self.steps):
            self.__add_nodes(graph)
        return graph


def write_test_dot(graph, out_fname=''):
    """Write build graph in dot format to `out_f` file-like object."""
    if not out_fname:
        now = datetime.now()
        out_fname = now.strftime('ybt_%2d_%2m_%Y_%2H_%2M_%2S_%f.dot')
    fout = open(out_fname, 'w')
    fout.write('strict digraph    {\n')
    clrs = nx.get_node_attributes(graph, 'color')
    stls = nx.get_node_attributes(graph, 'style')
    fclrs = nx.get_node_attributes(graph, 'fillcolor')
    for node in graph.nodes():
        s = '['
        if node in clrs:
            s = s + 'color=' + str(clrs[node]) + ','
        if node in stls:
            s = s + 'color=' + str(stls[node]) + ','
        if node in fclrs:
            s = s + 'color=' + str(fclrs[node]) + ','
        fout.write('  {} {}];\n'.format(node, s))
    fout.writelines('    {} -> {};\n'.format(u, v)
                    for u, v in graph.edges())
    fout.write('}\n\n')
    fout.close()
    print('Output file is "{}"'.format(out_fname))
    return out_fname


def dot_file_line_proc(graph, line):
    """ Parsing dot file line """
    edge = re.split(r'\s*->\s*', line)
    if len(edge) == 2:
        name = re.sub(r'\s+|;', '', edge[0]).strip('\"')
        child_name = re.sub(r'\s+|;', '', edge[1]).strip('\"')
        graph.add_edge(name, child_name)
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
            graph.add_node(name, **attributes)


def load_dot(in_fname):
    """ Read graph from dot format """
    with open(in_fname, 'r') as in_f:
        graph = nx.DiGraph()
        for line in in_f:
            dot_file_line_proc(graph, line)
    return graph
