package main

import (
  "os"
  "testing"

  "github.com/stretchr/testify/assert"
)

const (
  newName = "Sebastian"
)

func TestMain(m *testing.M) {
  initName(newName)
  os.Exit(m.Run())
}

func TestGoodbyeName(t *testing.T) {
  assert := assert.New(t)
  assert.Equal(newName, getName())
}
