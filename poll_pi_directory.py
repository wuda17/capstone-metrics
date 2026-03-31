#!/usr/bin/env python3
#
# HOW TO USE:
#
# ./poll_pi_directory.py \
# --remote-dir /home/sebastian/Documents/capstone/recordings/user \
# --local-dir ./pulled_files
#
from __future__ import annotations

import argparse
import atexit
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict


@dataclass
class RemoteFile:
    rel_path: str
    size: int
    mtime: float


def log(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def require_command(name: str) -> None:
    if not shutil_which(name):
        raise SystemExit(f"Required command not found in PATH: {name}")


def shutil_which(name: str) -> str | None:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


class PiDirectoryPoller:
    def __init__(
        self,
        host: str,
        remote_dir: str,
        local_dir: Path,
        interval: float,
        settle_seconds: float,
        recursive: bool,
        state_file: Path,
    ) -> None:
        self.host = host
        self.remote_dir = PurePosixPath(remote_dir)
        self.local_dir = local_dir
        self.interval = interval
        self.settle_seconds = settle_seconds
        self.recursive = recursive
        self.state_file = state_file
        self.control_path = Path(tempfile.gettempdir()) / f"pi-pull-{os.getpid()}.sock"
        self.observed: Dict[str, dict[str, float | int]] = {}
        self.downloaded: Dict[str, dict[str, float | int]] = self._load_state()
        self.master_started = False

    def _load_state(self) -> Dict[str, dict[str, float | int]]:
        if not self.state_file.exists():
            return {}
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log(f"State file is unreadable, starting fresh: {self.state_file}")
            return {}
        downloaded = data.get("downloaded")
        if not isinstance(downloaded, dict):
            return {}
        return downloaded

    def _save_state(self) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {"downloaded": self.downloaded}
            self.state_file.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"Could not write state file {self.state_file}: {exc.strerror or exc}") from exc

    def start_master_connection(self) -> None:
        command = [
            "ssh",
            "-fN",
            "-o",
            "BatchMode=no",
            "-o",
            "ControlMaster=yes",
            "-o",
            "ControlPersist=yes",
            "-o",
            f"ControlPath={self.control_path}",
            self.host,
        ]
        log(f"Opening SSH control connection to {self.host}. SSH may prompt once for a password or passphrase.")
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as exc:
            raise SystemExit(f"Failed to open SSH connection to {self.host}: {exc}") from exc
        self.master_started = True

    def close_master_connection(self) -> None:
        if not self.master_started:
            return
        command = [
            "ssh",
            "-O",
            "exit",
            "-o",
            f"ControlPath={self.control_path}",
            self.host,
        ]
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.master_started = False
        try:
            self.control_path.unlink()
        except FileNotFoundError:
            pass

    def _base_ssh_command(self) -> list[str]:
        return [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ControlMaster=auto",
            "-o",
            f"ControlPath={self.control_path}",
            self.host,
        ]

    def _base_scp_command(self) -> list[str]:
        return [
            "scp",
            "-q",
            "-p",
            "-o",
            "BatchMode=yes",
            "-o",
            "ControlMaster=auto",
            "-o",
            f"ControlPath={self.control_path}",
        ]

    def list_remote_files(self) -> Dict[str, RemoteFile]:
        depth_flag = "" if self.recursive else "-maxdepth 1"
        remote_command = (
            f"find -L {shlex.quote(str(self.remote_dir))} {depth_flag} "
            "-mindepth 1 -type f -printf '%P\\0%s\\0%T@\\0'"
        )
        command = [*self._base_ssh_command(), remote_command]
        try:
            result = subprocess.run(command, check=True, capture_output=True)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Remote listing failed: {stderr or exc}") from exc

        parts = result.stdout.split(b"\0")
        if parts and parts[-1] == b"":
            parts.pop()
        if len(parts) % 3 != 0:
            raise RuntimeError("Remote listing output was malformed.")

        files: Dict[str, RemoteFile] = {}
        for index in range(0, len(parts), 3):
            rel_path = parts[index].decode("utf-8", errors="surrogateescape")
            size = int(parts[index + 1].decode("ascii"))
            mtime = float(parts[index + 2].decode("ascii"))
            files[rel_path] = RemoteFile(rel_path=rel_path, size=size, mtime=mtime)
        return files

    def local_path_for(self, rel_path: str) -> Path:
        return self.local_dir / Path(rel_path)

    def local_matches_remote(self, rel_path: str, remote_file: RemoteFile) -> bool:
        local_path = self.local_path_for(rel_path)
        if not local_path.exists():
            return False
        stats = local_path.stat()
        if stats.st_size != remote_file.size:
            return False
        return abs(stats.st_mtime - remote_file.mtime) < 2.0

    def already_downloaded(self, rel_path: str, remote_file: RemoteFile) -> bool:
        record = self.downloaded.get(rel_path)
        if record:
            if int(record.get("size", -1)) == remote_file.size and abs(
                float(record.get("mtime", -1.0)) - remote_file.mtime
            ) < 0.001 and self.local_matches_remote(rel_path, remote_file):
                return True
        if self.local_matches_remote(rel_path, remote_file):
            self.downloaded[rel_path] = {"size": remote_file.size, "mtime": remote_file.mtime}
            return True
        return False

    def download(self, remote_file: RemoteFile) -> None:
        local_path = self.local_path_for(remote_file.rel_path)
        temp_path = local_path.with_name(local_path.name + ".part")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        remote_path = str(self.remote_dir / PurePosixPath(remote_file.rel_path))

        if temp_path.exists():
            temp_path.unlink()

        command = [
            *self._base_scp_command(),
            f"{self.host}:{remote_path}",
            str(temp_path),
        ]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
            raise
        os.replace(temp_path, local_path)
        self.downloaded[remote_file.rel_path] = {
            "size": remote_file.size,
            "mtime": remote_file.mtime,
        }
        self._save_state()

    def process_once(self) -> None:
        remote_files = self.list_remote_files()
        now = time.monotonic()

        missing = set(self.observed) - set(remote_files)
        for rel_path in missing:
            self.observed.pop(rel_path, None)

        for rel_path, remote_file in sorted(remote_files.items()):
            if self.already_downloaded(rel_path, remote_file):
                continue

            observed = self.observed.get(rel_path)
            if observed is None or observed["size"] != remote_file.size or observed["mtime"] != remote_file.mtime:
                self.observed[rel_path] = {
                    "size": remote_file.size,
                    "mtime": remote_file.mtime,
                    "stable_since": now,
                }
                log(f"Detected {rel_path} ({remote_file.size} bytes), waiting for it to settle.")
                continue

            stable_for = now - float(observed["stable_since"])
            if stable_for < self.settle_seconds:
                continue

            log(f"Downloading {rel_path} -> {local_path_display(self.local_path_for(rel_path))}")
            self.download(remote_file)
            self.observed.pop(rel_path, None)

    def run_forever(self) -> None:
        try:
            self.local_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise SystemExit(
                f"Could not create local directory {self.local_dir}: {exc.strerror or exc}. "
                "Use a writable path such as ~/pulled_files or ./pulled_files."
            ) from exc
        self.start_master_connection()
        atexit.register(self.close_master_connection)
        log(f"Watching {self.host}:{self.remote_dir} every {self.interval:.1f}s")
        log(f"Saving files into {local_path_display(self.local_dir)}")
        log(f"State file: {local_path_display(self.state_file)}")
        try:
            while True:
                try:
                    self.process_once()
                except Exception as exc:
                    log(f"Polling error: {exc}")
                time.sleep(self.interval)
        except KeyboardInterrupt:
            log("Stopping.")


def local_path_display(path: Path) -> str:
    return str(path.expanduser().resolve())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Poll a directory on a remote host over SSH and download newly added files "
            "after they stop changing."
        )
    )
    parser.add_argument(
        "--host",
        default="ferb-pi-tailscale",
        help="SSH host alias from ~/.ssh/config. Default: ferb-pi-tailscale",
    )
    parser.add_argument("--remote-dir", required=True, help="Directory on the Raspberry Pi to watch.")
    parser.add_argument("--local-dir", required=True, help="Local directory to save files into.")
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Polling interval in seconds. Default: 5",
    )
    parser.add_argument(
        "--settle-seconds",
        type=float,
        default=8.0,
        help="How long a file must stay unchanged before downloading. Default: 8",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Also watch subdirectories under the remote directory.",
    )
    parser.add_argument(
        "--state-file",
        help="Optional JSON file used to remember what has already been downloaded.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    require_command("ssh")
    require_command("scp")

    local_dir = Path(args.local_dir).expanduser()
    state_file = (
        Path(args.state_file).expanduser()
        if args.state_file
        else local_dir / ".pi_pull_state.json"
    )

    poller = PiDirectoryPoller(
        host=args.host,
        remote_dir=args.remote_dir,
        local_dir=local_dir,
        interval=args.interval,
        settle_seconds=args.settle_seconds,
        recursive=args.recursive,
        state_file=state_file,
    )
    poller.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
