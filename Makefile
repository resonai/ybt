PY?=python3

help:
	@echo 'Makefile for YABT                                           '
	@echo '                                                            '
	@echo 'Usage:                                                      '
	@echo '   make test     Run test suite with active Python and PEP8 '
	@echo '                                                            '

test:
	py.test --pep8 --cov=yabt

.PHONY: help test
