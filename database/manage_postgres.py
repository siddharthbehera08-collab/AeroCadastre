import subprocess
import sys
import time
from pathlib import Path
import psycopg2

PG_BIN = Path(r"D:\PostgreSQL\16\bin")
PG_DATA = Path(r"D:\PostgreSQL\data")
POSTGRES_EXE = PG_BIN / "postgres.exe"
PG_CTL_EXE = PG_BIN / "pg_ctl.exe"


def is_running() -> bool:
    try:
        conn = psycopg2.connect(
            host="127.0.0.1", port=5432, user="postgres", dbname="aerocadastre", connect_timeout=2
        )
        conn.close()
        return True
    except Exception:
        return False


def start() -> None:
    if is_running():
        print("PostgreSQL is already running.")
        return
    print("Starting PostgreSQL server...")
    log_file = PG_DATA / "server.log"
    cmd = [str(PG_CTL_EXE), "-D", str(PG_DATA), "-l", str(log_file), "start"]
    # If pg_ctl exits or needs detached process
    subprocess.Popen(
        [str(POSTGRES_EXE), "-D", str(PG_DATA)],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(15):
        time.sleep(1)
        if is_running():
            print("PostgreSQL started successfully on port 5432.")
            return
    print("PostgreSQL start timed out or failed. Check server.log.")


def stop() -> None:
    print("Stopping PostgreSQL server...")
    try:
        subprocess.run([str(PG_CTL_EXE), "-D", str(PG_DATA), "stop", "-m", "fast"], capture_output=True)
    except Exception:
        pass
    # Also ensure any lingering postgres process is stopped
    subprocess.run(["powershell", "-Command", "Stop-Process -Name postgres -Force -ErrorAction SilentlyContinue"], capture_output=True)
    print("PostgreSQL stopped.")


def status() -> None:
    if is_running():
        print("PostgreSQL status: RUNNING (127.0.0.1:5432)")
    else:
        print("PostgreSQL status: STOPPED")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        if action == "start":
            start()
        elif action == "stop":
            stop()
        elif action == "status":
            status()
        elif action == "restart":
            stop()
            time.sleep(2)
            start()
        else:
            print("Usage: python manage_postgres.py [start|stop|restart|status]")
    else:
        status()
