import subprocess
import threading
import time
from typing import List, Optional

class Supervisor:
    """Zero-dependency process supervisor with restart policies."""
    
    def __init__(self, command: List[str], restarts: int = 3, delay: int = 5):
        self.command = command
        self.restarts = restarts
        self.delay = delay
        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self._lock = threading.Lock()
        # Observability: the number of times a child has been launched, and
        # the pids it has run under. Without these the restart behaviour is
        # invisible: the whole restart cycle can finish between two samples
        # of the current process, so a test cannot tell a restart happened
        # from a single launch.
        self.restart_count = 0
        self.restart_history: List[int] = []
        # Set when the monitor dies from an unexpected error. Without it the
        # thread evaporates, ``running`` stays True, and a caller polling the
        # flag is told the service is up when it never started.
        self.last_error: Optional[BaseException] = None
        self._thread: Optional[threading.Thread] = None

    def _monitor(self):
        try:
            self._monitor_loop()
        except BaseException as exc:  # noqa: BLE001 - must not vanish silently
            self.last_error = exc
            raise
        finally:
            self.running = False

    def _monitor_loop(self):
        count = 0
        while self.running and count <= self.restarts:
            print(f"[Supervisor] Starting: {' '.join(self.command)} (Attempt {count+1})")
            try:
                with self._lock:
                    self.process = subprocess.Popen(self.command)
                    self.restart_count += 1
                    self.restart_history.append(self.process.pid)
            except OSError as exc:
                # Retrying cannot help, and dying quietly leaves the caller
                # believing the supervisor is alive.
                print(f"[Supervisor] Failed to start {self.command!r}: {exc}")
                self.last_error = exc
                self.running = False
                return

            self.process.wait()
            
            if not self.running:
                break
                
            print(f"[Supervisor] Process exited with code {self.process.returncode}")
            count += 1
            if count <= self.restarts:
                print(f"[Supervisor] Restarting in {self.delay}s...")
                time.sleep(self.delay)
        
        if count > self.restarts:
            print("[Supervisor] Max restarts reached. Giving up.")
        self.running = False

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            # A second start() used to spawn a second monitor that stop() had
            # no handle on: it kept restarting the command forever while both
            # threads raced over self.process.
            raise RuntimeError("Supervisor is already running")
        self.running = True
        self.last_error = None
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        with self._lock:
            if self.process:
                self.process.terminate()
        print("[Supervisor] Stopped.")

if __name__ == "__main__":
    # Example: supervise a simple echo loop
    sup = Supervisor(["python3", "-c", "import time; print('Pulse'); time.sleep(1); exit(1)"], restarts=2)
    sup.start()
    try:
        while sup.running:
            time.sleep(1)
    except KeyboardInterrupt:
        sup.stop()
