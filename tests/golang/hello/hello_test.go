package main

import "testing"

func TestGetGreet(t *testing.T) {
	if greet := getGreet("boomer"); greet != "hello boomer" {
		t.Errorf("Unexpected greeting \"%s\"", greet)
	}
}
