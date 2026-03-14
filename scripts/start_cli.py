import subprocess
import sys
from pathlib import Path
import signal


def main():
    root = Path(__file__).resolve().parent
    script = root / "start.sh"

    cmd = ["bash", str(script), *sys.argv[1:]]

    process = subprocess.Popen(cmd)

    try:
        process.wait()
    except KeyboardInterrupt:
        print("\nStopping services...")
        process.send_signal(signal.SIGINT)
        process.wait()
        sys.exit(130)