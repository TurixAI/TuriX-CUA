# winapp_launcher.py
import asyncio, json, os, re, subprocess, sys, time
from pathlib import Path
from typing import Optional

import win32com.client      # 解析 .lnk
import win32gui, win32process, win32con, pywintypes
import psutil
import win32com.shell.shell as shell
from rapidfuzz import fuzz, process

START_MENU_DIRS = [
    Path(os.environ["ProgramData"]) / r"Microsoft\Windows\Start Menu\Programs",
    Path(os.environ["APPDATA"])     / r"Microsoft\Windows\Start Menu\Programs",
]           # :contentReference[oaicite:0]{index=0}

INDEX_PATH = Path(__file__).with_name("app_index.json")
def _scan_shortcuts() -> list[dict]:
    shell_dispatch = win32com.client.Dispatch("WScript.Shell")
    apps = []
    for root in START_MENU_DIRS:
        for p in root.rglob("*.lnk"):
            lnk = shell_dispatch.CreateShortCut(str(p))
            target = os.path.expandvars(lnk.Targetpath or "")
            apps.append({
                "name": p.stem,
                "exe":  target if Path(target).exists() else None,
                "args": lnk.Arguments or "",
                "cwd":  lnk.WorkingDirectory or "",
                "lnk":  str(p)
            })
    return apps

def build_index(force=False) -> None:
    if INDEX_PATH.exists() and not force:
        return
    index = _scan_shortcuts()
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2))

def _load_index() -> list[dict]:
    build_index()
    return json.loads(INDEX_PATH.read_text())

def resolve_app(name: str) -> Optional[dict]:
    idx = _load_index()
    cand = [app for app in idx if name.lower() in app["name"].lower()]
    if cand:
        return sorted(cand, key=lambda a: len(a["name"]))[0]
    names = [app["name"] for app in idx]
    best = process.extractOne(name, names, scorer=fuzz.QRatio)
    if best and best[1] > 60:        
        return next(a for a in idx if a["name"] == best[0])
    return None

def _sysnative_fix(path: str) -> str:

    if sys.maxsize > 2**32: 
        return path
    system32 = os.path.join(os.environ["SystemRoot"], "System32").lower()
    if path.lower().startswith(system32):
        return path.replace("System32", "Sysnative", 1)
    return path

def _shell_execute(path: str,
                   params: str = "",
                   cwd: str = "") -> tuple[bool, str]:
    try:
        shell.ShellExecuteEx(
            fMask=0,
            hwnd=None,
            lpVerb="open",
            lpFile=_sysnative_fix(path),
            lpParameters=params,
            lpDirectory=cwd,
            nShow=win32con.SW_SHOWNORMAL)
        return True, "shell execute ok"
    except pywintypes.error as e:
        if e.winerror == 1223:
            return False, "User canceled UAC"
        return False, f"ShellExecute error {e.winerror}: {e.strerror}"


async def _launch_record(rec: dict) -> tuple[bool, str]:
    lnk = rec.get("lnk")
    exe = rec.get("exe")
    args = rec.get("args", "")
    cwd  = rec.get("cwd", "")


    if lnk and Path(lnk).exists():
        try:
            os.startfile(lnk)
            return True, ".lnk opened"
        except OSError as e:
            msg = f"os.startfile failed: {e}"

    # 2) ShellExecute 
    if exe:
        ok, msg2 = _shell_execute(exe, args, cwd)
        if ok:
            return True, msg2
        msg = f"exe shell failed: {msg2}"

    # 3) subprocess.Popen exe
    if exe and Path(exe).exists():
        try:
            subprocess.Popen([exe] + args.split(),
                             cwd=cwd or None, shell=False,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "subprocess exe ok"
        except OSError as e:
            msg = f"subprocess exe error: {e}"

    # 4) ShellExecute 
    ok, msg2 = _shell_execute(rec["name"])
    if ok:
        return True, msg2
    msg = f"name shell failed: {msg2}"

    # 5) subprocess.Popen 
    try:
        subprocess.Popen([rec["name"]],
                         shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, "subprocess name ok"
    except OSError as e:
        msg = f"name subprocess error: {e}"

    return False, msg

async def open_application_by_name(app_name: str,
                                   bring_to_front: bool = True) -> tuple[bool, str]:
    rec = resolve_app(app_name)
    if not rec:
        return False, "not found in index"

    ok, info = await _launch_record(rec)
    if ok and bring_to_front:
        await asyncio.sleep(0.4)
        _activate_window_by_exe(Path(rec.get("exe", rec["name"])).name)

    # logger.info("open_app '%s' -> %s", app_name, info if ok else "FAILED")
    return ok, info

def _activate_window_by_exe(exe_name: str):
    exe_name = exe_name.lower()

    def enum_handler(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                p = psutil.Process(pid)
                if exe_name in p.name().lower():
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    return False
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return True
    win32gui.EnumWindows(enum_handler, None)
