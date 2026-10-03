from __future__ import annotations

import ctypes
import argparse
import queue
import re
import socket
import subprocess
import sys
import threading
import time
import winreg
from pathlib import Path


LAUNCHER_DIR = Path(__file__).resolve().parent
T3_EXE = LAUNCHER_DIR / "runtime" / "t3.exe"
DEFAULT_URL = "http://localhost:3773"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3773
LOG_FILE = LAUNCHER_DIR / "t3-launcher.log"
MUTEX_NAME = r"Local\T3CodeWindowsLauncher"

CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
ERROR_ALREADY_EXISTS = 183

ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
PAIRING_URL = re.compile(
    r"https?://(?:localhost|127\.0\.0\.1):\d+/pair\?token=[^\s]+",
    re.IGNORECASE,
)
TOKEN = re.compile(r"(?<=token=)[^\s]+", re.IGNORECASE)


def redact(text: str) -> str:
    return TOKEN.sub("[REDACTED]", text)


def write_log(message: str) -> None:
    try:
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > 512_000:
            backup = LOG_FILE.with_suffix(".log.old")
            backup.unlink(missing_ok=True)
            LOG_FILE.replace(backup)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] {redact(message).rstrip()}\n")
    except OSError:
        pass


def show_error(message: str) -> None:
    write_log(f"ERRO: {message}")
    ctypes.windll.user32.MessageBoxW(None, message, "T3 Code", 0x10)


def port_is_open(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except OSError:
        return False


def find_chrome() -> Path | None:
    registry_locations = (
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
    )
    for hive, key_name in registry_locations:
        try:
            with winreg.OpenKey(hive, key_name) as key:
                candidate = Path(winreg.QueryValue(key, None))
                if candidate.exists():
                    return candidate
        except OSError:
            continue

    candidates = (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe",
    )
    return next((path for path in candidates if path.exists()), None)


def open_in_chrome(url: str, app_mode: bool = True) -> None:
    chrome = find_chrome()
    try:
        if chrome:
            arguments = [str(chrome)]
            if app_mode:
                arguments.extend([f"--app={url}", "--start-maximized"])
            else:
                arguments.append(url)
            subprocess.Popen(
                arguments,
                creationflags=CREATE_NO_WINDOW,
                close_fds=True,
            )
        else:
            import os

            os.startfile(url)
        write_log(f"Navegador aberto: {redact(url)}")
    except OSError as exc:
        show_error(f"Não foi possível abrir o Google Chrome.\n\n{exc}")


def acquire_mutex() -> tuple[int, bool]:
    kernel32 = ctypes.windll.kernel32
    kernel32.SetLastError(0)
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    return handle, kernel32.GetLastError() != ERROR_ALREADY_EXISTS


def wait_for_existing_server(
    seconds: float = 20.0,
    open_browser: bool = True,
) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if port_is_open():
            if open_browser:
                open_in_chrome(DEFAULT_URL)
            return True
        time.sleep(0.25)
    return False


def stream_output(process: subprocess.Popen[str], lines: queue.Queue[str | None]) -> None:
    assert process.stdout is not None
    try:
        for line in process.stdout:
            lines.put(line)
    finally:
        lines.put(None)


def launch_t3(server_only: bool = False) -> int:
    if port_is_open():
        if not server_only:
            open_in_chrome(DEFAULT_URL)
        return 0

    mutex, owns_mutex = acquire_mutex()
    if not owns_mutex:
        if not wait_for_existing_server(open_browser=not server_only):
            show_error("O T3 está a iniciar, mas o servidor ainda não respondeu.")
            return 1
        return 0

    try:
        if not T3_EXE.exists():
            show_error(f"O executável do T3 não foi encontrado:\n\n{T3_EXE}")
            return 1

        write_log(f"A iniciar T3: {T3_EXE}")
        process = subprocess.Popen(
            [str(T3_EXE)],
            cwd=str(T3_EXE.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
        )

        lines: queue.Queue[str | None] = queue.Queue()
        reader = threading.Thread(
            target=stream_output,
            args=(process, lines),
            daemon=True,
        )
        reader.start()

        opened = server_only
        started = time.monotonic()
        output_finished = False

        while process.poll() is None or not output_finished:
            try:
                line = lines.get(timeout=0.15)
            except queue.Empty:
                line = ""

            if line is None:
                output_finished = True
            elif line:
                clean = ANSI_ESCAPE.sub("", line).strip()
                if clean:
                    write_log(clean)
                    pairing = PAIRING_URL.search(clean)
                    if pairing and not opened:
                        open_in_chrome(pairing.group(0).rstrip(".,;"))
                        opened = True

            if not opened and time.monotonic() - started >= 8 and port_is_open():
                open_in_chrome(DEFAULT_URL)
                opened = True

            if process.poll() is not None and output_finished:
                break

        exit_code = process.returncode or 0
        write_log(f"T3 terminou com código {exit_code}")
        return exit_code
    except OSError as exc:
        show_error(f"Não foi possível iniciar o T3.\n\n{exc}")
        return 1
    finally:
        if mutex:
            ctypes.windll.kernel32.CloseHandle(mutex)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lançador invisível do T3 Code")
    parser.add_argument(
        "--server-only",
        action="store_true",
        help="Inicia o servidor sem abrir a interface",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_arguments()
    sys.exit(launch_t3(server_only=arguments.server_only))
