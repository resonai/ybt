package hello_lib

import (
	"flag"
  "testing"

	"github.com/stretchr/testify/assert"

  hello "bar.com/hello_lib"
)

var (
	greetTo = flag.String("greet_to", "wrong", "Greetings To")
)

func TestGetGreet(t *testing.T) {
	greet := hello.GetGreet("boomer")
	assert.Equalf(t, "hello boomer", greet, "Unexpected greeting \"%s\"", greet)
}

func TestPrintFooFromEnv(t *testing.T) {
	greet := hello.PrintFooFromEnv()
	assert.Equalf(t, "hello foo", greet, "Unexpected greeting \"%s\"", greet)
}

func TestGetGreetFromFlag(t *testing.T) {
	greet := hello.GetGreet(*greetTo)
	assert.Equalf(t, "hello boomer", greet, "Unexpected greeting \"%s\"", greet)
}
