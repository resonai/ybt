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
import random

import networkx


def generate_random_dag(nodes, min_rank=0, max_rank=10, edge_prob=0.3):
    """Return a random DAG with nodes from `nodes`.

    and edges can only go from nodes[i] -> nodes[j] if i < j
    (guaranteeing DAGness).
    """
    g = networkx.DiGraph()
    g.add_nodes_from(nodes)
    for j in range(1, len(nodes)):
        rank = random.randint(min_rank, min(j, max_rank))
        g.add_edges_from((nodes[i], nodes[j])
                         for i in random.sample(range(j), k=rank)
                         if random.random() > edge_prob)
    return g
