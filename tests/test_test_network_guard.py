from __future__ import annotations

import socket
import unittest


class TestNetworkGuardTests(unittest.TestCase):
    def test_test_suite_blocks_unexpected_network(self) -> None:
        from tests.network_guard import NetworkBlockedError, install_network_guard

        install_network_guard()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with self.assertRaises(NetworkBlockedError):
                sock.connect(("93.184.216.34", 80))
        finally:
            sock.close()


if __name__ == "__main__":
    unittest.main()

