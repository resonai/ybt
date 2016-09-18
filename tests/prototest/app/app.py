
from flask import Flask
from proto.app_hello.app import hello_pb2

APP = Flask(__name__)


@APP.route('/')
def home():
    hello = hello_pb2.Hello()
    hello.world = 'foo'
    return str(hello)


if '__main__' == __name__:
  APP.run(host='0.0.0.0', port=5000, debug=True)
