"""Apply Wetrix device-selector and two-player frontend integration."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1]
patch=root/'patches/frontend-two-player.patch'
command=['git','-C',str(root/'lib/RecompFrontend'),'apply']
if subprocess.run(command+['--reverse','--check',str(patch)],capture_output=True).returncode:
    subprocess.run(command+['--check',str(patch)],check=True)
    subprocess.run(command+[str(patch)],check=True)
