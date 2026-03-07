#!/usr/bin/env python3
"""Generate a multi-size Windows .ico from curated YinYang PNG assets."""

from __future__ import annotations

from pathlib import Path
import struct


def _entry(width: int, height: int, data_len: int, data_offset: int) -> bytes:
    # ICO directory entry. width/height of 256 are encoded as 0.
    w = 0 if width == 256 else width
    h = 0 if height == 256 else height
    return struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, data_len, data_offset)


def build_ico(pngs: list[Path], out_path: Path) -> None:
    blobs = [p.read_bytes() for p in pngs]
    count = len(blobs)

    header = struct.pack("<HHH", 0, 1, count)
    dir_size = 6 + count * 16

    entries: list[bytes] = []
    offset = dir_size
    for p, blob in zip(pngs, blobs):
        size = int(p.stem.rsplit("-", 1)[-1])
        entries.append(_entry(size, size, len(blob), offset))
        offset += len(blob)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(header + b"".join(entries) + b"".join(blobs))


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src = repo_root / "web" / "images" / "yinyang"
    out_path = repo_root / "resources" / "windows" / "solace-browser.ico"

    sizes = [16, 32, 48, 64, 128, 256]
    pngs = [src / f"yinyang-logo-{s}.png" for s in sizes]

    missing = [str(p) for p in pngs if not p.exists()]
    if missing:
        raise SystemExit(f"Missing icon source PNG(s): {missing}")

    build_ico(pngs, out_path)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
