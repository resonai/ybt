package main

import (
	"flag"
	"github.com/common-nighthawk/go-figure"

	helloLib "bar.com/hello_lib"
)

func main() {
	who := flag.String("who", "world", "who to greet")
	flag.Parse()

    greet := helloLib.GetGreet(*who)
    myFigure := figure.NewFigure(greet, "", true)
    myFigure.Print()
}
