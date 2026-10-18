# Kobra BO2 Update Compat Patch — public patcher
#
# Created by julian (2026). GPL-3.0, same as the Kobra/Greyhound/Wraith lineage.
#
# What it does:
#   1. Verifies the SHA-256 of your local Kobra.exe (safety gate).
#   2. Applies two byte-level changes documented in PATCH_EVIDENCE.md.
#   3. Writes "Kobra-patched.exe" next to the input. Never modifies the original.
#
# Usage:
#   python patch_kobra.py                                   # patch .\Kobra.exe
#   python patch_kobra.py --input "C:\path\Kobra.exe" --output "C:\out"
#   python patch_kobra.py --verify [--input "C:\path\Kobra.exe"]
#
import argparse
import hashlib
import json
import os
import sys

# -- Only this exact Kobra.exe build is supported -------------------------------
ORIGINAL_SHA256 = "b983a3b0a7269786542af3394f887963a0e9bc20033a1abb8c97e1d66d4a8dc1"
PATCHED_SHA256 = "d42882bedf0fa4a6fe31e1fbc5d61837f8c3172d899d6e53c95e49ab1a1ba811"

# -- Patch 1: signature string in .rdata (fixed length, spaces preserved) -------
SIG_FILE_OFFSET = 2170064
SIG_OLD = b"56 51 FF D2 8B F0 83 C4 04 85 F6"
SIG_NEW = b"53 51 FF D2 8B D8 83 C4 04 85 DB"

# -- Patch 2: read-offset displacement in the scan routine ----------------------
# Product reference: FUN at VA 0x14005AE58, instruction "LEA RDX, [R14 + 0x3B]".
# File offset of the instruction start (369240); the displacement byte is +3.
LEA_FILE_OFFSET = 369240
LEA_OLD = bytes.fromhex("498D563B")   # lea rdx,[r14+0x3B]
LEA_NEW = bytes.fromhex("498D5628")   # lea rdx,[r14+0x28]


def sha256_of(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def apply_patches(data):
    problems = []
    if data[SIG_FILE_OFFSET:SIG_FILE_OFFSET + len(SIG_OLD)] != SIG_OLD:
        problems.append("signature string site does not match")
    if data[LEA_FILE_OFFSET:LEA_FILE_OFFSET + 4] != LEA_OLD:
        problems.append("read-offset instruction does not match")
    if problems:
        raise SystemExit(
            "ERROR: file does not match the expected layout:\n  "
            + "\n  ".join(problems)
            + "\nRefusing to patch a different/unexpected build."
        )

    out = bytearray(data)
    out[SIG_FILE_OFFSET:SIG_FILE_OFFSET + len(SIG_NEW)] = SIG_NEW
    out[LEA_FILE_OFFSET:LEA_FILE_OFFSET + 4] = LEA_NEW
    return bytes(out)


def main():
    ap = argparse.ArgumentParser(
        description="Patch Kobra.exe for the current Black Ops II Steam build."
    )
    ap.add_argument("--input", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "Kobra.exe"),
                    help="path to the official, unmodified Kobra.exe")
    ap.add_argument("--output", default=None,
                    help="output path (default: Kobra-patched.exe next to the input)")
    ap.add_argument("--verify", action="store_true",
                    help="only report what the file is; do not write anything")
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        raise SystemExit("ERROR: input file not found: %s" % args.input)

    data = open(args.input, "rb").read()
    current = hashlib.sha256(data).hexdigest()

    if args.verify:
        if current == ORIGINAL_SHA256:
            print("OK: this is the unpatched supported build.")
            print("     apply the patch with:  python patch_kobra.py")
        elif current == PATCHED_SHA256:
            print("OK: this file is already patched.")
        else:
            print("UNKNOWN build (sha256 %s)." % current)
            print("This patcher documents only the release it was made for;")
            print("it refuses other builds on purpose.")
        return

    if current == PATCHED_SHA256:
        print("Nothing to do: the input is already the patched build.")
        return

    out_path = args.output or (os.path.splitext(args.input)[0] + "-patched.exe")
    patched = apply_patches(data)
    patched_sha = hashlib.sha256(patched).hexdigest()

    with open(out_path, "wb") as f:
        f.write(patched)

    receipt = {
        "input_sha256": current,
        "output_sha256": patched_sha,
        "patches": [
            {"kind": "sig1-string", "file_offset": SIG_FILE_OFFSET,
             "old_ascii": SIG_OLD.decode(), "new_ascii": SIG_NEW.decode()},
            {"kind": "lea-disp8", "file_offset": LEA_FILE_OFFSET,
             "old_bytes": LEA_OLD.hex().upper(), "new_bytes": LEA_NEW.hex().upper()},
        ],
    }
    with open(out_path + ".receipt.json", "w") as f:
        json.dump(receipt, f, indent=2)

    print("Patched OK.")
    print("  input : %s (%s)" % (args.input, current))
    print("  output: %s (%s)" % (out_path, patched_sha))
    print("Start the game, run the patched exe and click Load Game.")


if __name__ == "__main__":
    main()
