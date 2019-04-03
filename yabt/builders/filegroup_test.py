import pytest

from yabt.buildcontext import BuildContext
from yabt.graph import populate_targets_graph

slow = pytest.mark.skipif(not pytest.config.getoption('--with-slow'),
                          reason='need --with-slow option to run')


@slow
@pytest.mark.usefixtures('in_cpp_project')
def test_file_group_dep(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['hello:hello-with-data']
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph(run_tests=True)
