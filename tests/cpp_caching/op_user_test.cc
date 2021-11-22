#include "op_user_lib.h"

#include <gtest/gtest.h>

TEST(OpUserTest, Test) {
  ASSERT_EQ(12, use_op());
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
