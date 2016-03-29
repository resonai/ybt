# -*- coding: utf-8 -*-

"""
yabt target graph tests
~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2016 Yowza by Itamar Ostricher
:license: MIT, see LICENSE for more details.
"""


import pytest

from .buildcontext import BuildContext
from .graph import populate_targets_graph, topological_sort


@pytest.mark.usefixtures('in_dag_project')
def test_load_builders2(basic_conf):
    populate_targets_graph(basic_conf)
    assert (
        set(['yapi/server:users', ':flask', ':gunicorn', 'common:logging',
             'fe:fe', 'yapi/server:yapi', 'yapi/server:yapi-gunicorn',
             'common:base']) == set(BuildContext.target_graph.nodes()))
    assert (
        set([('fe:fe', 'yapi/server:users'), ('fe:fe', ':flask'),
             ('fe:fe', 'common:base'), ('yapi/server:yapi', ':flask'),
             ('yapi/server:yapi', 'common:base'),
             ('yapi/server:yapi-gunicorn', 'yapi/server:yapi'),
             ('yapi/server:yapi-gunicorn', 'common:base'),
             ('yapi/server:yapi-gunicorn', ':gunicorn'),
             ('common:base', 'common:logging')]) ==
        set(BuildContext.target_graph.edges()))
    # Can't assert the list directly, because it is not stable / deterministic
    topo_sort = list(topological_sort(BuildContext.target_graph))

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
