
import os

from pytest import yield_fixture

import yabt


def yabt_project_fixture(project):
  orig_dir = os.getcwd()
  tests_work_dir = os.path.abspath(
      os.path.join(os.path.dirname(__file__), 'tests', project))
  os.chdir(tests_work_dir)
  yield
  os.chdir(orig_dir)


@yield_fixture
def in_simple_project():
  yield from yabt_project_fixture('simple')


@yield_fixture
def in_dag_project():
  yield from yabt_project_fixture('dag')


@yield_fixture
def basic_conf():
  yield yabt.cli.init_and_get_conf([])
