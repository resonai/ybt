package main

import (
	"flag"
	"fmt"
)

func getGreet(who string) string {
	return fmt.Sprintf("hello %s", who)
}

func main() {
	who := flag.String("who", "world", "who to greet")
	flag.Parse()
	greet := getGreet(*who)
	fmt.Printf("%s\n", greet)
}
