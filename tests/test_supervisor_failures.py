"""Regression tests for supervisor lifecycle defects found 2026-11-03."""
import sys
import time

import pytest
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tiny_supervisor import Supervisor


def test_a_missing_command_does_not_leave_running_true_forever():
    """A supervisor that cannot start its command must not claim to be running.

    Before the fix ``FileNotFoundError`` was raised inside the monitor thread
    and lost. ``running`` stayed ``True`` while the thread was dead, so any
    caller polling ``is_running`` was told the service was up when nothing had
    ever started.
    """
    sup = Supervisor(["/nonexistent/binary-for-regression-test"], restarts=1, delay=0)
    sup.start()
    time.sleep(0.6)
    assert sup.running is False, "running must be False once the monitor dies"
    assert sup._thread.is_alive() is False
    assert sup.last_error is not None, "the failure must be reported, not swallowed"


def test_starting_twice_does_not_leak_an_unstoppable_thread():
    """Two ``start()`` calls must not leave a supervisor nobody can stop.

    Before the fix the second ``start()`` rebound ``self._thread``, so
    ``stop()`` could only reach the newest monitor. The first kept restarting
    the command with no handle on it, while both threads raced over
    ``self.process``.
    """
    sup = Supervisor(["sleep", "2"], restarts=4, delay=0.1)
    sup.start()
    first = sup._thread

    with pytest.raises(RuntimeError):
        sup.start()
    assert sup._thread is first, "the first handle must survive the refusal"

    sup.stop()
    deadline = time.time() + 5
    while first.is_alive() and time.time() < deadline:
        time.sleep(0.05)
    assert first.is_alive() is False, "stop() must stop the only monitor"


def test_stop_is_idempotent_and_safe_before_start():
    sup = Supervisor(["sleep", "5"])
    sup.stop()  # must not raise
    sup.start()
    time.sleep(0.1)
    sup.stop()
    sup.stop()  # must not raise
