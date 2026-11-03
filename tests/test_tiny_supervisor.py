import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tiny_supervisor import Supervisor


def _py(code):
    """A python command that runs the given source."""
    return [sys.executable, "-c", code]


class TestConstruction(unittest.TestCase):
    def test_defaults(self):
        sup = Supervisor(["echo", "hi"])
        self.assertEqual(sup.restarts, 3)
        self.assertEqual(sup.delay, 5)
        self.assertFalse(sup.running)

    def test_custom_values(self):
        sup = Supervisor(["echo", "hi"], restarts=5, delay=1)
        self.assertEqual(sup.restarts, 5)
        self.assertEqual(sup.delay, 1)

    def test_process_is_none_before_start(self):
        sup = Supervisor(["echo", "hi"])
        self.assertIsNone(sup.process)


class TestLifecycle(unittest.TestCase):
    def test_start_launches_process(self):
        sup = Supervisor(_py("import time; time.sleep(30)"), restarts=0, delay=0)
        sup.start()
        try:
            deadline = time.time() + 5
            while sup.process is None and time.time() < deadline:
                time.sleep(0.02)
            self.assertIsNotNone(sup.process)
            self.assertIsNone(sup.process.poll())
        finally:
            sup.stop()

    def test_stop_terminates_process(self):
        sup = Supervisor(_py("import time; time.sleep(30)"), restarts=0, delay=0)
        sup.start()
        deadline = time.time() + 5
        while sup.process is None and time.time() < deadline:
            time.sleep(0.02)
        pid = sup.process.pid
        sup.stop()
        deadline = time.time() + 5
        while sup.process.poll() is None and time.time() < deadline:
            time.sleep(0.02)
        self.assertIsNotNone(sup.process.poll())
        self.assertIsNotNone(pid)

    def test_stop_without_start_is_safe(self):
        sup = Supervisor(["echo", "hi"])
        sup.stop()
        self.assertFalse(sup.running)


class TestRestarts(unittest.TestCase):
    def test_process_is_restarted_after_exit(self):
        # Exits immediately with code 3, so it should be relaunched.
        #
        # Assert on restart_count, not on the current pid. A polling loop
        # looking for a changed pid races with the supervisor: with delay=0
        # the whole cycle of launches can finish between two samples, so the
        # test would report "never restarted" even though it was.
        sup = Supervisor(_py("import sys; sys.exit(3)"), restarts=2, delay=0)
        sup.start()
        try:
            deadline = time.time() + 15
            while sup.restart_count < 2 and time.time() < deadline:
                time.sleep(0.02)
            self.assertGreaterEqual(
                sup.restart_count, 2, "process was never restarted"
            )
            self.assertGreaterEqual(
                len(set(sup.restart_history)), 2, "restart reused the same pid"
            )
        finally:
            sup.stop()

    def test_restart_count_starts_at_zero(self):
        sup = Supervisor(_py("import sys; sys.exit(0)"))
        self.assertEqual(sup.restart_count, 0)
        self.assertEqual(sup.restart_history, [])

    def test_restart_count_matches_launches(self):
        sup = Supervisor(_py("import sys; sys.exit(1)"), restarts=2, delay=0)
        sup.start()
        try:
            deadline = time.time() + 15
            while sup.running and time.time() < deadline:
                time.sleep(0.02)
            # restarts=2 means one initial launch plus two restarts.
            self.assertEqual(sup.restart_count, 3)
            self.assertEqual(len(sup.restart_history), 3)
        finally:
            sup.stop()

    def test_gives_up_after_max_restarts(self):
        sup = Supervisor(_py("import sys; sys.exit(1)"), restarts=1, delay=0)
        sup.start()
        deadline = time.time() + 15
        while sup.running and time.time() < deadline:
            time.sleep(0.05)
        self.assertFalse(sup.running, "supervisor kept running past its restart budget")

    def test_stop_halts_further_restarts(self):
        sup = Supervisor(_py("import sys; sys.exit(1)"), restarts=50, delay=1)
        sup.start()
        time.sleep(0.4)
        sup.stop()
        time.sleep(0.5)
        self.assertFalse(sup.running)


if __name__ == "__main__":
    unittest.main()
