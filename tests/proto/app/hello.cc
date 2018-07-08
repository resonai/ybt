#include <fstream>
#include <iostream>

#include "proto/app/hello.pb.h"

int main(int argc, char* argv[]) {
    // Verify that the version of the library that we linked against is
    // compatible with the version of the headers we compiled against.
    GOOGLE_PROTOBUF_VERIFY_VERSION;

    tests::Hello hello;
    // Read & parse serialized message
    std::fstream input("hello.pb", std::ios::in | std::ios::binary);
    if (!hello.ParseFromIstream(&input)) {
        return -1;
    }

    // Print out the message
    std::cout << hello.message();

    // Optional:  Delete all global objects allocated by libprotobuf.
    google::protobuf::ShutdownProtobufLibrary();

    return 0;
}
