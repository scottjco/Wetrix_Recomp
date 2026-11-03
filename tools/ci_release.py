"""Verified ROM-free generated-source snapshots and audited release archives."""
import argparse, hashlib, io, json, os, shutil, subprocess, tarfile, zipfile
from pathlib import Path, PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
GENERATED=["funcs_0.c","funcs.h","unimplemented.cpp","dispatch.inl","runtime_services.h","aspMain.cpp"]
INPUTS=["config/runtime.toml","config/audio.toml","WetrixRecompSyms/runtime.syms.toml","tools/finalize_runtime.py"]
ARCHIVE=ROOT/"generated/recompiled-source.tar.gz"
MANIFEST=ROOT/"generated/manifest.json"
VERSION="0.1.1"
HD_ARCHIVE=ROOT/"generated/hd-textures.zip"
HD_HASH=ROOT/"generated/hd-textures.sha256"
def digest(data): return hashlib.sha256(data).hexdigest()
def input_digest(path): return digest(path.read_bytes().replace(b"\r\n",b"\n"))
def audit(name,data):
    p=PurePosixPath(name)
    if p.suffix.lower() in {".z64",".n64",".v64",".rom",".mpk",".sav",".srm",".eep",".fla"} or any(x.lower() in {"saves","save-backups","user"} for x in p.parts):
        raise ValueError(f"Forbidden private/game asset: {name}")
    if data[:4] in {b"\x80\x37\x12\x40",b"\x37\x80\x40\x12",b"\x40\x12\x37\x80"}: raise ValueError(f"ROM header: {name}")
def snapshot():
    ARCHIVE.parent.mkdir(exist_ok=True)
    files={}
    with tarfile.open(ARCHIVE,"w:gz") as archive:
        for name in GENERATED:
            data=(ROOT/"build/generated-runtime"/name).read_bytes()
            audit(name,data)
            entry=tarfile.TarInfo("build/generated-runtime/"+name)
            entry.size=len(data);entry.mode=0o644;entry.mtime=0
            archive.addfile(entry,io.BytesIO(data));files[entry.name]=digest(data)
    MANIFEST.write_text(json.dumps({"format":1,"archive_sha256":digest(ARCHIVE.read_bytes()),"files":files,"inputs":{n:input_digest(ROOT/n) for n in INPUTS}},indent=2)+"\n")
    print("Snapshotted six translated source/header files; no ROM/data blobs")
def prepare():
    manifest=json.loads(MANIFEST.read_text())
    if digest(ARCHIVE.read_bytes())!=manifest["archive_sha256"]: raise ValueError("Source archive hash mismatch")
    for n,h in manifest["inputs"].items():
        if input_digest(ROOT/n)!=h: raise ValueError("Stale source snapshot: "+n)
    pending={}
    allowed={"build/generated-runtime/"+n for n in GENERATED}
    with tarfile.open(ARCHIVE) as archive:
        for item in archive:
            if not item.isfile() or item.name not in allowed or item.name in pending: raise ValueError("Unexpected source entry")
            data=archive.extractfile(item).read();audit(item.name,data)
            if digest(data)!=manifest["files"].get(item.name): raise ValueError("Source hash mismatch")
            pending[item.name]=data
    if set(pending)!=allowed or set(manifest["files"])!=allowed: raise ValueError("Incomplete source snapshot")
    for n,data in pending.items():
        target=ROOT/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    print("Verified and restored translated sources without ROM")
def bundle_hd_textures(stage):
    if digest(HD_ARCHIVE.read_bytes()) != HD_HASH.read_text().split()[0]:
        raise ValueError("HD archive hash mismatch")
    prefix="Textures/hd-sprites/"
    with zipfile.ZipFile(HD_ARCHIVE) as archive:
        seen=set()
        for entry in archive.infolist():
            if entry.is_dir(): continue
            path=PurePosixPath(entry.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in entry.filename:
                raise ValueError("Unsafe HD archive path")
            if entry.filename in seen: raise ValueError("Duplicate HD archive path")
            seen.add(entry.filename)
            data=archive.read(entry)
            audit(entry.filename,data)
            if not entry.filename.startswith(prefix):
                if entry.filename!="README.txt": raise ValueError("Unexpected HD archive entry")
                continue
            if path.suffix.lower() not in {".png",".json",".txt"}:
                raise ValueError("Unexpected HD file type")
            target=stage/path
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(data)
    pack=stage/"Textures/hd-sprites"
    database=json.loads((pack/"rt64.json").read_text())
    hashes=set()
    for texture in database["textures"]:
        key=texture["hashes"]["rt64"]
        if key in hashes: raise ValueError("Duplicate HD texture hash")
        hashes.add(key)
        target=pack/texture["path"]
        if not target.suffix: target=target.with_suffix(".png")
        if not target.resolve().is_relative_to(pack.resolve()) or not target.is_file():
            raise ValueError("Missing or unsafe HD texture reference")
    if not (pack/"RIGHTS-AND-AI.txt").is_file(): raise ValueError("HD rights notice missing")

def package(build,platform,arch):
    name=f"WetrixRecompiled-{VERSION}-{platform}-{arch}"
    stage=ROOT/"dist"/name
    if stage.exists(): raise ValueError("Refusing stale package directory")
    stage.mkdir(parents=True)
    executable="Wetrix.exe" if platform=="Windows" else "Wetrix"
    shutil.copy2(build/executable,stage/executable)
    if platform=="Windows":
        for n in ["SDL2.dll","dxcompiler.dll","dxil.dll"]: shutil.copy2(build/n,stage/n)
        redist=Path(os.environ["VCToolsRedistDir"])
        crt=sorted(redist.glob("x64/Microsoft.VC*.CRT"))[-1]
        for n in ["msvcp140.dll","msvcp140_atomic_wait.dll","vcruntime140.dll","vcruntime140_1.dll"]: shutil.copy2(crt/n,stage/n)
    if platform=="macOS":
        # Recursively bundle Homebrew dependencies and rewrite install names.
        libs=stage/"lib";libs.mkdir()
        queue=[stage/executable];seen=set()
        while queue:
            binary=queue.pop()
            if binary in seen: continue
            seen.add(binary)
            lines=subprocess.check_output(["otool","-L",str(binary)],text=True).splitlines()[1:]
            for line in lines:
                dependency=line.strip().split(" (",1)[0]
                if dependency.startswith(("/opt/homebrew/","/usr/local/")):
                    target=libs/Path(dependency).name
                    if not target.exists(): shutil.copy2(dependency,target);queue.append(target)
                    relative="@executable_path/lib/"+target.name if binary==stage/executable else "@loader_path/"+target.name
                    subprocess.run(["install_name_tool","-change",dependency,relative,str(binary)],check=True)
            if binary!=stage/executable: subprocess.run(["install_name_tool","-id","@loader_path/"+binary.name,str(binary)],check=True)
        for binary in list(libs.iterdir())+[stage/executable]: subprocess.run(["codesign","--force","--sign","-",str(binary)],check=True)
    bundle_hd_textures(stage)
    shutil.copytree(ROOT/"Assets/menu",stage/"assets")
    shutil.copy2(ROOT/"resources/wetrix.ico",stage/"Wetrix.ico")
    shutil.copy2(ROOT/"resources/NOTICE.txt",stage/"licenses-icon.txt")
    if platform!="Windows":
        launcher=stage/("Run Wetrix.command" if platform=="macOS" else "Run Wetrix.sh")
        launcher.write_text('#!/bin/sh\ncd -- "$(dirname -- "$0")" || exit 1\nexec ./Wetrix\n')
        launcher.chmod(0o755)
    for n in ["README.md","CHANGELOG.md","LICENSE","THIRD_PARTY_NOTICES.md"]:
        if (ROOT/n).is_file(): shutil.copy2(ROOT/n,stage/n)
    for p in (ROOT/"lib").rglob("*"):
        if p.is_file() and ".git" not in p.parts and p.name.lower().startswith(("license","licence","copying","notice")):
            dest=stage/"licenses"/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    if (ROOT/"release-notices").is_dir(): shutil.copytree(ROOT/"release-notices",stage/"licenses/extra")
    (stage/"RUNNING.txt").write_text("Run Wetrix.exe directly on Windows (no command script needed), or the Run Wetrix launcher on Linux/macOS. If Assets/data.z64 is missing, a file picker opens; select your supported Wetrix ROM and it will be verified and imported locally. Extract to a writable directory. HD textures are included and enabled by default for fresh profiles. No ROM, save or personal settings are included. Linux requires SDL2, GTK3, FreeType, Vulkan and a supported GPU driver. macOS binaries are ad-hoc signed, not notarized.\n")
    revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    (stage/"BUILD-INFO.txt").write_text(f"Version: {VERSION}\nCommit: {revision}\nPlatform: {platform} {arch}\n")
    for p in stage.rglob("*"):
        if p.is_file(): audit(p.relative_to(stage).as_posix(),p.read_bytes())
    output=stage.parent/(stage.name+(".tar.gz" if platform=="Linux" else ".zip"))
    if platform=="Linux":
        with tarfile.open(output,"w:gz") as archive: archive.add(stage,arcname=name)
    else:
        with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED) as archive:
            for p in stage.rglob("*"):
                if p.is_file(): archive.write(p,name+"/"+p.relative_to(stage).as_posix())
    output.with_name(output.name+".sha256").write_text(digest(output.read_bytes())+"  "+output.name+"\n")
    print(output)
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("command",choices=["snapshot","prepare","package"])
    parser.add_argument("--build",type=Path,default=ROOT/"build-release");parser.add_argument("--platform",choices=["Windows","Linux","macOS"]);parser.add_argument("--arch",default="x64")
    args=parser.parse_args()
    if args.command=="snapshot": snapshot()
    elif args.command=="prepare": prepare()
    else:
        if not args.platform: parser.error("package requires --platform")
        package(args.build,args.platform,args.arch)
