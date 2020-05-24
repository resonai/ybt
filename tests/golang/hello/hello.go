package main

import (
	"flag"
	"fmt"
	"github.com/common-nighthawk/go-figure"
)

func GetGreet(who string) string {
	return fmt.Sprintf("hello %s", who)
}

func main() {
	who := flag.String("who", "world", "who to greet")
	flag.Parse()

  greet := GetGreet(*who)
  myFigure := figure.NewFigure(greet, "", true)
  myFigure.Print()
}
