package main

import (
	"flag"
	"fmt"
	"os"
	"github.com/common-nighthawk/go-figure"
)
func PrintFooFromEnv() string {
	v := os.Getenv("FOO")
	return fmt.Sprintf("hello %s", v)
}


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
