package hello_lib

import (
    "os"
    "fmt"
)

func PrintFooFromEnv() string {
	v := os.Getenv("FOO")
	return fmt.Sprintf("hello %s", v)
}

func GetGreet(who string) string {
	return fmt.Sprintf("hello %s", who)
}
