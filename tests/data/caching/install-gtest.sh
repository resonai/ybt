set -e

cd googletest-release-1.8.0/googletest
clang++-5.0 -isystem include -pthread -I. -c src/gtest-all.cc
ar -rv libgtest.a gtest-all.o
cp libgtest.a /usr/lib
mv include/gtest /usr/include/
