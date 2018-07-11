from proto.app.hello_pb2 import Hello


def get_message(msg_file):
    hello = Hello()
    with open(msg_file, 'rb') as f:
        hello.ParseFromString(f.read())
    return hello.message


if __name__ == '__main__':
    print(get_message('hello.pb'))
