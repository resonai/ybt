PYTHON?=python3
BASEDIR=$(CURDIR)

help:
	@echo 'Makefile for YABT                                                  '
	@echo '                                                                   '
	@echo 'Usage:                                                             '
	@echo '   make test     Run test suite with active Python and PEP8        '
	@echo '   make lint     Check style for project and tests                 '
	@echo '   make dist     Build source & wheel distributions                '
	@echo '   make clean    Clean build & dist output directories             '
	@echo '   make pypi     Clean, build dist, and upload to PyPI (twine)     '
	@echo '                                                                   '

test:
	py.test --pep8 --cov=yabt

tox:
	TOXENV=py34,py35 tox

lint:
	pylint yabt

dist:
	${PYTHON} setup.py sdist bdist_wheel
	@echo "Finished buliding source & wheel distributions"

clean:
	rm -r $(BASEDIR)/build $(BASEDIR)/dist
	@echo "Finished cleaning build & dist output dirs"

pypi: clean dist
	twine upload dist/*
	@echo "Finished uploading version to PyPI"

.PHONY: help test tox lint dist clean pypi
