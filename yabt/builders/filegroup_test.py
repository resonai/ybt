import pytest
from subprocess import check_output

from yabt.buildcontext import BuildContext
from yabt.graph import populate_targets_graph


@pytest.mark.slow
@pytest.mark.usefixtures('in_cpp_project')
def test_file_group_dep(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = ['hello:hello-with-data']
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph(run_tests=True)
    ls_output_image = str(check_output(
        ['docker', 'run', '--rm', '--entrypoint', 'ls',
         build_context.targets['hello:hello-with-data'].image_id,
         '-R', 'hello/data']))
    ls_output_here = str(check_output(['ls', '-R', 'hello/data']))
    assert ls_output_image == ls_output_here
