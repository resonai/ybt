package goodbye_lib

var (
  libName = "Bill"
)

func GetGoodbyeName() string {
  return libName
}

func SetGoodbyeName(newName string) {
  libName = newName
}
