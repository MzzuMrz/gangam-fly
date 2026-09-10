"""Prepare pinned public dependencies and verified MaleCNS data, sequentially.

Run inside the installed project environment: python -m gangnamfly.prepare.
Downloads about 1.1 GB of data plus anatomical body assets. No cloud training.
"""

import hashlib
import json
import subprocess
import sys

from .config import DOOM, ROOT

SOURCES = {
    "doomfly": ("https://github.com/nftechie/doomfly.git", "71ecf53d78eaffaf1a57ed7b0ccf5d458abc9f33"),
    "flybody": ("https://github.com/TuragaLab/flybody.git", "d015e9bfe441bd90ae431bac24c55cb74bdbce26"),
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    for name, (url, revision) in SOURCES.items():
        destination = ROOT / "vendor" / name
        if not destination.exists():
            subprocess.run(["git", "clone", "--no-checkout", url, str(destination)], check=True)
            subprocess.run(["git", "checkout", "--detach", revision], cwd=destination, check=True)
        current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=destination, text=True).strip()
        if current != revision:
            raise RuntimeError(
                f"{destination} is at {current}; expected {revision}. Preserve your checkout and prepare the pinned revision explicitly."
            )
    lock = json.loads((DOOM / "data-provenance/malecns_v1/source.lock.json").read_text())
    target = DOOM / "connectome_data/malecns_v1"
    target.mkdir(parents=True, exist_ok=True)
    for name, record in lock.items():
        path = target / name
        if not path.exists():
            partial = path.with_suffix(".download")
            print(f"Downloading {name}: {record['bytes']:,} bytes", flush=True)
            subprocess.run(
                ["curl", "--fail", "--location", "--retry", "3", "--output", str(partial), record["url"]],
                check=True,
            )
            if digest(partial) != record["sha256"]:
                raise RuntimeError(f"Checksum mismatch: {partial}")
            partial.replace(path)
        if digest(path) != record["sha256"]:
            raise RuntimeError(f"Checksum mismatch: {path}")
    (target / "source.lock.json").write_text(json.dumps(lock, indent=2) + "\n")
    sys.path.insert(0, str(DOOM))
    from doom.connectome import import_graph
    from doom.prepare import prepare

    import_graph("malecns_v1")
    prepare("malecns_v1")
    subprocess.run([sys.executable, str(DOOM / "doom/build_kernel.py")], check=True)
    from .prepare_demo import CAPTURE
    from .prepare_demo import prepare as prepare_dance

    if not CAPTURE.exists():
        prepare_dance()
    print("Verified connectome and native kernel ready. Build web/ and run python -m gangnamfly.main.")


if __name__ == "__main__":
    main()
