package goodbye_lib

import (
  "testing"

  "github.com/stretchr/testify/assert"

  "bar.com/goodbye_lib"
)

func runGoodbyeLibTest(t *testing.T, prevName, newName string) {
  assert := assert.New(t)
  assert.Equal(prevName, goodbye_lib.GetGoodbyeName())
  goodbye_lib.SetGoodbyeName(newName)
  assert.Equal(newName, goodbye_lib.GetGoodbyeName())
}
