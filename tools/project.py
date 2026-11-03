"""Verify the local ROM and guard the N64Recomp generation step."""
import argparse
import hashlib
from pathlib import Path
import struct
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SHA256 = "790f36a3ddd64e4dcd08c479b0b66f9080d0191473e92fa895f53d15706167bb"


def verify():
    config = tomllib.loads((ROOT / "wetrix.us.toml").read_text())["input"]
    rom = ROOT / config["rom_file_path"]
    data = rom.read_bytes()
    if len(data) != 8388608 or data[:4] != bytes.fromhex("80371240"):
        raise ValueError("Expected the inspected 8 MiB big-endian Wetrix ROM")
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError("ROM SHA-256 differs from the inspected revision; do not reuse its mappings")
    entry = struct.unpack_from(">I", data, 8)[0]
    if config["entrypoint"] != entry:
        raise ValueError("Configuration entrypoint differs from ROM header")
    print(f"ROM verified: {data[32:52].decode('ascii').strip()}, {len(data)} bytes")
    print(f"Cartridge ID: {data[59:63].decode('ascii')}; revision: {data[63]}; header entry: 0x{entry:08X}")
    print(f"SHA-256: {digest}")
    return config, data


def check_symbols(config, data):
    path = ROOT / config["symbols_file_path"]
    if not path.is_file():
        raise ValueError(f"Missing Wetrix function/section map: {path}. See WetrixRecompSyms/README.md")
    sections = tomllib.loads(path.read_text()).get("section", [])
    names = set()
    found_entry = False
    for section in sections:
        start, size, rom = section["vram"], section["size"], section["rom"]
        if size <= 0 or rom < 0 or rom + size > len(data):
            raise ValueError(f"Invalid ROM section bounds: {section['name']}")
        for func in section.get("functions", []):
            addr, length, name = func["vram"], func["size"], func["name"]
            if name in names or length <= 0 or addr % 4 or length % 4:
                raise ValueError(f"Invalid or duplicate function: {name}")
            if not start <= addr < addr + length <= start + size:
                raise ValueError(f"Function outside section: {name}")
            names.add(name)
            found_entry |= addr == config["entrypoint"]
    if not names or not found_entry:
        raise ValueError("Symbol map must contain functions including the entrypoint")
    print(f"Basic symbol bounds verified: {len(sections)} sections, {len(names)} functions")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["verify", "check", "recompile"])
    parser.add_argument("--tool", type=Path)
    args = parser.parse_args()
    config, data = verify()
    if args.action != "verify":
        check_symbols(config, data)
    if args.action == "recompile":
        if args.tool is None or not args.tool.is_file():
            raise ValueError("Supply --tool pointing to a built N64Recomp executable")
        (ROOT / config["output_func_path"]).mkdir(exist_ok=True)
        subprocess.run([str(args.tool.resolve()), str(ROOT / "wetrix.us.toml")], cwd=ROOT, check=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
