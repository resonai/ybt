PYTHON?=python3
BASEDIR=$(CURDIR)

help:
	@echo 'Makefile for YABT                                                    '
	@echo '                                                                     '
	@echo 'Usage:                                                               '
	@echo '   make test       Run full test suite with active Python and FLAKE8 '
	@echo '   make quicktest  Run test suite with active Python and FLAKE8      '
	@echo '   make lint       Check style for project and tests                 '
	@echo '   make dist       Build source & wheel distributions                '
	@echo '   make clean      Clean build & dist output directories             '
	@echo '   make pypi       Clean, build dist, and upload to PyPI (twine)     '
	@echo '   make release    Bump version, tag & push (trigger Travis deploy)  '
	@echo '                                                                     '

test:
	py.test --flake8 --cov=yabt --with-slow

quicktest:
	py.test --flake8 --cov=yabt

tox:
	TOXENV=py34,py35,py36 tox

lint:
	pylint yabt

dist:
	${PYTHON} setup.py sdist bdist_wheel
	@echo "Finished buliding source & wheel distributions"

clean:
	rm -rf $(BASEDIR)/build $(BASEDIR)/dist
	@echo "Finished cleaning build & dist output dirs"

cleancache:
	find tests \( -name yabtwork -o -name ybt_bin \) -type d -exec rm -rf "{}" \;
	@echo "Finished deleting all yabtwork & ybt_bin dirs"

pypi: clean dist
	twine upload dist/*
	@echo "Finished uploading version to PyPI"

release:
	./scripts/release.sh

.PHONY: help test tox lint dist clean pypi release
