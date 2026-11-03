"""Apply the pinned RT64 compatibility patch, preserving unrelated edits."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
patch = root / 'patches/rt64-rdram-vertices.patch'
command = ['git', '-C', str(root / 'lib/rt64'), 'apply']
if subprocess.run(command + ['--reverse', '--check', str(patch)], capture_output=True).returncode:
    subprocess.run(command + ['--check', str(patch)], check=True)
    subprocess.run(command + [str(patch)], check=True)
