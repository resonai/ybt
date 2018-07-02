#include <boost/asio.hpp>
#include <boost/asio/spawn.hpp>

#include <iostream>

using boost::asio::ip::tcp;
using boost::asio::yield_context;

int main() {
    boost::asio::io_service svc;

    tcp::acceptor a(svc);
    a.open(tcp::v4());
    a.set_option(tcp::acceptor::reuse_address(true));
    a.bind({{}, 6767});  // bind to port 6767 on localhost
    a.listen(5);

    spawn(svc, [&a](yield_context yield) {
        while (1) {
            tcp::socket s(a.get_io_service());
            a.async_accept(s, yield);

            spawn(yield, [s = std::move(s)](yield_context yield) mutable {
                // do a read
                char buf[1024] = {};
                size_t bytes = s.async_read_some(
                    boost::asio::buffer(buf), yield);
                std::cout << "Echo to " << s.remote_endpoint() << ": "
                    << std::string(buf, buf+bytes) << std::endl;
                bytes = async_write(s, boost::asio::buffer(buf), yield);
            });
        }
    });
    svc.run();  // wait for shutdown (Ctrl-C or failure)
}
