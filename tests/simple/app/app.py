#!/usr/local/bin/python

from flask import Flask


APP = Flask(__name__)


@APP.route('/')
def home():
  return 'Hello!'


if '__main__' == __name__:
  APP.run(host='0.0.0.0', port=5000, debug=True)
