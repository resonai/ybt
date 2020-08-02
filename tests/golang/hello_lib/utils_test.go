package hello_lib

import (
    "testing"

    hello "bar.com/hello_lib"
)

func TestGetGreet(t *testing.T) {
	if greet := hello.GetGreet("boomer"); greet != "hello boomer" {
		t.Errorf("Unexpected greeting \"%s\"", greet)
	}
}

func TestPrintFooFromEnv(t *testing.T) {
	if greet := hello.PrintFooFromEnv(); greet != "hello foo" {
		t.Errorf("Unexpected greeting \"%s\"", greet)
	}
}
