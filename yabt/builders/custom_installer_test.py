from subprocess import check_output
import pytest

from yabt.buildcontext import BuildContext
from yabt.graph import populate_targets_graph


@pytest.mark.slow
@pytest.mark.usefixtures('in_custom_installer_project')
def test_custom_installer_args(basic_conf):
    build_context = BuildContext(basic_conf)
    basic_conf.targets = [':w00t']
    populate_targets_graph(build_context, basic_conf)
    build_context.build_graph(run_tests=True)
    w00t_content = check_output(
        ['docker', 'run', '--rm', '--entrypoint', 'cat',
         build_context.targets[':w00t'].image_id, '/var/opt/w00t'])
    assert w00t_content == b'hello there\nhow are you doing\n'
