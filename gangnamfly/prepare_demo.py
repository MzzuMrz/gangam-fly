"""Prepare Xsens' public continuous Gangnam Style capture for local experiments."""

import argparse
import hashlib
import io
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

import numpy as np

from .config import ROOT
from .episode import save_npz

SOURCE_URL = "https://www.xsens.com/hubfs/Downloads/Data/Gangnam%20Style.zip"
SOURCE_PAGE = "https://www.xsens.com/resources/news/motion-capture-files-for-psy-gangnam-style"
SOURCE_SHA256 = "a9f8b4f97e23db799055464ccd705ed448f6dc712aa1f775aa34f3ac2d2a85de"
# Digests are over the decoded, canonical little-endian arrays.  The archive
# label alone is not an authentication mechanism: an NPZ can be edited while
# retaining its source_sha256 field.
ARRAY_SHA256 = {
    "time": "f678dd7f38a6c47c7b9387b486422cfd1bc7ca416294d697e707a87e6ecb8f13",
    "positions": "48bc5c40aae02ca613376e41dafd4858031a67059049c03951b5c78089121d27",
    "orientations": "2d252c7af7f72ce677bc0b19f9ad25b1d859cb1327fbc87c4dce2c6126cb4308",
    "segments": "a7a1c81e86d9e233ba4339122f1efff7e43e8227e008439d49eac2da02925ac4",
}
SEGMENT_LABELS = (
    "Pelvis",
    "L5",
    "L3",
    "T12",
    "T8",
    "Neck",
    "Head",
    "RightShoulder",
    "RightUpperArm",
    "RightForeArm",
    "RightHand",
    "LeftShoulder",
    "LeftUpperArm",
    "LeftForeArm",
    "LeftHand",
    "RightUpperLeg",
    "RightLowerLeg",
    "RightFoot",
    "RightToe",
    "LeftUpperLeg",
    "LeftLowerLeg",
    "LeftFoot",
    "LeftToe",
)
CAPTURE = ROOT / "vendor/xsens/gangnam.npz"


def validate_capture(time, positions, orientations, segments, source_sha256):
    if np.asarray(source_sha256).item() != SOURCE_SHA256:
        raise ValueError("Unexpected motion-capture provenance")
    if time.shape != (7451,) or positions.shape != (7451, 23, 3) or orientations.shape != (7451, 23, 4):
        raise ValueError("Unexpected motion-capture schema")
    if segments.shape != (23,) or tuple(segments.astype(str)) != SEGMENT_LABELS:
        raise ValueError("Unexpected motion-capture labels")
    for name, value in (
        ("time", time),
        ("positions", positions),
        ("orientations", orientations),
        ("segments", segments),
    ):
        if hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest() != ARRAY_SHA256[name]:
            raise ValueError(f"Authenticated capture array mismatch: {name}")
    if not np.isfinite(time).all() or not np.isfinite(positions).all() or not np.isfinite(orientations).all():
        raise ValueError("Nonfinite capture values")
    if time[0] < 0 or time[-1] != 31.07 or np.any(np.diff(time) <= 0):
        raise ValueError("Unexpected capture timestamps")
    norms = np.linalg.norm(orientations, axis=2)
    if np.any(norms < 0.9999) or np.any(norms > 1.0001):
        raise ValueError("Invalid capture quaternions")


def prepare(archive=None):
    if archive is None:
        with urllib.request.urlopen(SOURCE_URL, timeout=45) as response:
            raw = response.read(16 * 1024 * 1024)
    else:
        raw = archive.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Xsens archive checksum does not match the inspected capture")
    with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
        xml = bundle.read("PSY Gangnam Style.mvnx")
    root = ET.fromstring(xml)
    segments = [s.attrib["label"] for s in root.findall(".//{*}segment")]
    frames = [f for f in root.findall(".//{*}frame") if f.get("type") == "normal"]
    times = np.array([float(f.attrib["time"]) / 1000 for f in frames])
    positions = np.array(
        [np.fromstring(f.findtext("{*}position", ""), sep=" ").reshape(23, 3) for f in frames], np.float32
    )
    orientations = np.array(
        [np.fromstring(f.findtext("{*}orientation", ""), sep=" ").reshape(23, 4) for f in frames], np.float32
    )
    validate_capture(times, positions, orientations, np.array(segments), SOURCE_SHA256)
    CAPTURE.parent.mkdir(parents=True, exist_ok=True)
    save_npz(
        CAPTURE,
        time=times,
        positions=positions,
        orientations=orientations,
        segments=np.array(segments),
        source_sha256=np.array(SOURCE_SHA256),
    )
    print(f"Prepared {len(frames)} frames, {times[-1]:.2f} s: {CAPTURE}")


def main():
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Use a local copy of the pinned Xsens ZIP")
    args = parser.parse_args()
    prepare(args.archive)


if __name__ == "__main__":
    main()
