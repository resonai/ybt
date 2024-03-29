package main

import (
	"flag"
	"fmt"
	"github.com/golang/protobuf/proto"
	pb "foo.com/ybtproto/app"
)

func main() {
	who := flag.String("who", "world", "who to greet")
	flag.Parse()
	msg := fmt.Sprintf("hello %s", *who)
	greet := &pb.Hello{Message: msg}
	fmt.Println(proto.MarshalTextString(greet))
}
