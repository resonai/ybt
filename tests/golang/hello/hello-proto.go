package main

import (
	"flag"
	"fmt"
	"github.com/golang/protobuf/proto"
	pb "proto/base_protos"
)

func getGreet(who string) pb.Hello {
	msg := fmt.Sprintf("hello %s", who)
	return pb.Hello{Message: &msg}
}

func main() {
	who := flag.String("who", "world", "who to greet")
	flag.Parse()
	msg := fmt.Sprintf("hello %s", *who)
	greet := &pb.Hello{Message: &msg}
	fmt.Println(proto.MarshalTextString(greet))
}
