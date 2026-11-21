#!/usr/bin/env python3
"""Install this skill where the platform expects it.

    python install.py                 # copy into /app/submission
    python install.py --target DIR    # copy somewhere else
    python install.py --force         # overwrite an existing SKILL.md

Idempotent: an existing SKILL.md at the target is left alone unless --force is
given, so running the installer twice cannot quietly replace a newer skill.
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {"_selftest", "__pycache__", ".git"}
SKIP_EXT = {".pyc", ".zip"}


def copy_tree(src, dst, force):
    copied, kept = [], []
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith("_")]
        rel = os.path.relpath(root, src)
        target_dir = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(target_dir, exist_ok=True)
        for name in files:
            if os.path.splitext(name)[1] in SKIP_EXT:
                continue
            s, d = os.path.join(root, name), os.path.join(target_dir, name)
            if os.path.exists(d) and not force:
                kept.append(os.path.relpath(d, dst))
                continue
            shutil.copy2(s, d)
            copied.append(os.path.relpath(d, dst))
    return copied, kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="/app/submission")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    target = a.target
    try:
        os.makedirs(target, exist_ok=True)
    except PermissionError:
        sys.exit("cannot write to %s; pass --target with a writable directory" % target)

    existed = os.path.exists(os.path.join(target, "SKILL.md"))
    copied, kept = copy_tree(HERE, target, a.force)
    print("target: %s" % os.path.abspath(target))
    print("copied: %d file(s)" % len(copied))
    if kept:
        print("kept existing: %d file(s)%s" % (
            len(kept), " (use --force to overwrite)" if existed and not a.force else ""))
    if not os.path.exists(os.path.join(target, "SKILL.md")):
        sys.exit("SKILL.md did not land in %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main())

