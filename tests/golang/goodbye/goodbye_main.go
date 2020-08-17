package main

import (
  "fmt"
)

var (
  name = "no-one"
)

func initName(newName string) {
  name = newName
}

func getName() string {
  return name
}

func main() {
  initName("Bill")
  fmt.Println("Goodbye,", getName())
}
