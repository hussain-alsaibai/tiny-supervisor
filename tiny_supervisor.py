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

    def _monitor(self):
        count = 0
        while self.running and count <= self.restarts:
            print(f"[Supervisor] Starting: {' '.join(self.command)} (Attempt {count+1})")
            with self._lock:
                self.process = subprocess.Popen(self.command)
            
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
        self.running = True
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
