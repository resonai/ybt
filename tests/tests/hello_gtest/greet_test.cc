#include "hello_gtest/greet.h"

#include <gtest/gtest.h>

TEST(GreetTest, GreetsByName) {
  ASSERT_EQ("Hello Ender", get_greet("Ender"));
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
