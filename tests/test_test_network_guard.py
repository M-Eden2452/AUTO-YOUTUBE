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


class NetworkGuardScopeTests(unittest.TestCase):
    """PLAN-STAB-3: the offline suite's baseline guard (installed once by
    ``tests/__init__.py``) must never end up disabled because one test's
    local install/uninstall pair ran. ``network_guard_scope`` is the safe
    replacement for raw install()/uninstall() pairs in test bodies.
    """

    def test_guard_is_active_on_entry_and_still_active_after_a_successful_scope(self) -> None:
        from tests import network_guard

        self.assertTrue(network_guard._installed, "baseline guard must be active before this test runs")
        with network_guard.network_guard_scope():
            self.assertTrue(network_guard._installed)
        self.assertTrue(network_guard._installed)

    def test_guard_is_restored_after_an_exception_inside_the_scope(self) -> None:
        from tests import network_guard

        with self.assertRaises(ValueError):
            with network_guard.network_guard_scope():
                self.assertTrue(network_guard._installed)
                raise ValueError("boom")
        self.assertTrue(network_guard._installed)

    def test_next_test_does_not_inherit_a_disabled_guard(self) -> None:
        """Simulates a module with a scoped exception followed by the next
        test in the process: the baseline guard must still protect it."""
        from tests import network_guard

        with network_guard.network_guard_scope():
            pass
        # Whatever the "next test" is, it observes the same active baseline
        # the offline suite established at process start - not a leaked-off
        # guard from this one.
        self.assertTrue(network_guard._installed)

    def test_scope_starting_from_an_uninstalled_baseline_fully_restores_originals(self) -> None:
        """Exercises the not-yet-installed branch without leaking an off
        state into later tests: the baseline is reinstalled in `finally`."""
        from tests import network_guard

        network_guard.uninstall_network_guard()
        try:
            self.assertFalse(network_guard._installed)
            with network_guard.network_guard_scope():
                self.assertTrue(network_guard._installed)
                self.assertIs(socket.socket.connect, network_guard._guarded_connect)
            self.assertFalse(network_guard._installed)
            self.assertIs(socket.socket.connect, network_guard._original_connect)
            self.assertIs(socket.create_connection, network_guard._original_create_connection)
            self.assertIs(socket.getaddrinfo, network_guard._original_getaddrinfo)
        finally:
            # Restore the process-wide baseline this offline run depends on.
            network_guard.install_network_guard()
        self.assertTrue(network_guard._installed)

    def test_install_uninstall_have_no_setup_failure_path(self) -> None:
        """install_network_guard()/uninstall_network_guard() only assign
        module attributes - they cannot themselves fail mid-way, so there is
        no separate setup/fixture-failure path to characterize beyond the
        exception-inside-scope case above. Idempotent repetition is safe."""
        from tests import network_guard

        for _ in range(3):
            network_guard.install_network_guard()
        self.assertTrue(network_guard._installed)


if __name__ == "__main__":
    unittest.main()

