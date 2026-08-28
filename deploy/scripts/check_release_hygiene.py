from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[2]
ALLOWED_CSV = {Path("surnasdes26/data/demo.csv")}
BLOCKED_NAMES = {
    ".env",
    ".env.local",
    "dashboard.sqlite3",
}
BLOCKED_SUFFIXES = {
    ".bak",
    ".dump",
    ".key",
    ".p12",
    ".pem",
    ".pfx",
    ".sav",
    ".sql",
    ".sqlite",
    ".sqlite3",
    ".zip",
}
SECRET_PATTERNS = {
    "private key": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "GitHub token": re.compile(rb"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "AWS access key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
}


def candidate_files() -> list[Path]:
    command = [
        "git",
        "-C",
        str(PROJECT_DIR),
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode == 0:
        names = [name for name in result.stdout.decode().split("\0") if name]
        return [PROJECT_DIR / name for name in names]
    raise RuntimeError("Repository Git belum diinisialisasi. Jalankan: git init -b main")


def inspect(path: Path) -> list[str]:
    relative = path.relative_to(PROJECT_DIR)
    problems: list[str] = []

    if path.name in BLOCKED_NAMES:
        problems.append("nama file terlarang")
    if path.suffix.lower() in BLOCKED_SUFFIXES:
        problems.append(f"ekstensi terlarang {path.suffix.lower()}")
    if path.suffix.lower() == ".csv" and relative not in ALLOWED_CSV:
        problems.append("CSV bukan demo sintetis")

    if not problems and path.stat().st_size <= 5 * 1024 * 1024:
        content = path.read_bytes()
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                problems.append(f"indikasi {label}")

    return [f"{relative.as_posix()}: {problem}" for problem in problems]


def main() -> int:
    try:
        files = candidate_files()
    except RuntimeError as exc:
        print(f"RELEASE HYGIENE: GAGAL — {exc}", file=sys.stderr)
        return 1
    problems = [problem for path in files for problem in inspect(path)]

    print(f"File kandidat Git: {len(files)}")
    if problems:
        print("RELEASE HYGIENE: GAGAL", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1

    print("RELEASE HYGIENE: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
