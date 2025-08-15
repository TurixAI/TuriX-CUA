import asyncio, json, os, re, subprocess, sys, time
from pathlib import Path
from typing import Optional

import win32com.client
import win32gui, win32process, win32con, pywintypes,win32api
import psutil
import win32com.shell.shell as shell
from rapidfuzz import fuzz, process
import ctypes

program_data = os.environ.get("ProgramData", "C:\\ProgramData")
appdata = os.environ.get("APPDATA", "C:\\Users\\Default\\AppData\\Roaming")
if not program_data or not appdata:
    raise RuntimeError("Environment variables ProgramData or APPDATA are not set.")
START_MENU_DIRS = [
    Path(program_data) / r"Microsoft\Windows\Start Menu\Programs",
    Path(appdata)     / r"Microsoft\Windows\Start Menu\Programs",
]

INDEX_PATH = Path(__file__).with_name("app_index.json")

_BUILTIN_EXES = [
    "notepad.exe", "cmd.exe", "powershell.exe", "wt.exe",
    "mspaint.exe", "write.exe", "wordpad.exe",
    "regedit.exe", "taskmgr.exe", "explorer.exe",
]

def _scan_builtin_apps() -> list[dict]:
    sys32 = Path(os.environ["SystemRoot"]) / "System32"
    apps  = []
    for exe in _BUILTIN_EXES:
        p = sys32 / exe
        if p.exists():
            apps.append({
                "name": p.stem,
                "exe":  str(p),
                "args": "",
                "cwd":  str(sys32),
                "lnk":  None
            })
    return apps

def _filter_apps(apps: list[dict]) -> list[dict]:
    seen   : set[str] = set()
    useful : list[dict] = []

    IGNORE_KEYWORDS = ("uninstall", "setup", "installer",
                       "帮助", "帮助文档", "documentation", "readme")

    for app in apps:
        exe = app.get("exe") or ""
        if not exe or not Path(exe).exists():
            continue
        if any(k in exe.lower() for k in IGNORE_KEYWORDS):
            continue

        key = exe.lower()
        if key in seen:
            continue
        seen.add(key)
        useful.append(app)

    return useful

user32 = ctypes.WinDLL("user32", use_last_error=True)

def _force_foreground(hwnd: int) -> None:
    fg_thread = win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())[0]
    this_thread = win32api.GetCurrentThreadId()
    if user32.AttachThreadInput(this_thread, fg_thread, True):
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
            win32gui.SetForegroundWindow(hwnd)
        finally:
            user32.AttachThreadInput(this_thread, fg_thread, False)

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

def build_index(force=True) -> None:
    if INDEX_PATH.exists() and not force:
        return
    index = _scan_shortcuts()
    index += _scan_builtin_apps()
    index = _filter_apps(index)
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2),
                          encoding="utf-8-sig")

def _load_index() -> list[dict]:
    build_index()
    return json.loads(INDEX_PATH.read_text(encoding="utf-8-sig"))

def list_applications() -> list[dict]:
    """List all applications in the Start Menu."""
    idx = _load_index()
    names = sorted({app["name"] for app in idx}, key=str.lower)
    return names

def resolve_app(name: str) -> Optional[dict]:
    idx = _load_index()
    cand = [app for app in idx if name.lower() in app["name"].lower()]
    if cand:
        return sorted(cand, key=lambda a: len(a["name"]))[0]
    # Fuzzy match if no exact match found
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

    # Try to activate the existing window first
    exe_name: Optional[str] = None
    if rec.get("exe"):
        try:
            exe_name = Path(rec["exe"]).name
        except Exception:
            exe_name = None

    title_hint = rec.get("name")

    if bring_to_front:
        if _activate_window(exe_name, title_hint):
            return True, "activated existing window"

    ok, info = await _launch_record(rec)
    if not ok:
        return False, info

    if bring_to_front:
        for _ in range(40):
            if _activate_window(exe_name, title_hint):
                return True, "launched and activated window"
            await asyncio.sleep(0.05)

    return True, info


def _activate_window_by_exe(exe_name: str) -> bool:
    exe_key = exe_name.lower() if exe_name else None
    return _activate_window(exe_key, None)


def _activate_hwnd(hwnd: int) -> None:
    """Restore + bring to foreground, with fallback."""
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
        win32gui.SetForegroundWindow(hwnd)
    except pywintypes.error:
        _force_foreground(hwnd)

def _best_existing_hwnd(exe_name: Optional[str],
                        title_hint: Optional[str]) -> Optional[int]:
    """
    Find the most appropriate top-level window:
    Prioritizes matching the process name (exe_name fragment matching, suitable for differences such as wt.exe / WindowsTerminal.exe)
    Falls back to fuzzy matching of the title if the exe is unavailable (suitable for UWP / AppsFolder shortcuts)
    Filters tool windows, prioritizing non-minimized windows
    """
    exe_key = exe_name.lower() if exe_name else None
    candidates: list[int] = []

    def enum_handler(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True

        matched = False

        # 1) name match
        if exe_key:
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                pname = psutil.Process(pid).name().lower()
                if exe_key in pname or pname in exe_key:
                    matched = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # 2) Title fuzzy matching
        if not matched and title_hint:
            try:
                if fuzz.QRatio(title_hint.lower(), title.lower()) >= 80:
                    matched = True
            except Exception:
                pass

        if matched:
            exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if exstyle & win32con.WS_EX_TOOLWINDOW:
                return True
            candidates.append(hwnd)
        return True

    win32gui.EnumWindows(enum_handler, None)

    for h in candidates:
        if not win32gui.IsIconic(h):
            return h
    return candidates[0] if candidates else None

def _activate_window(exe_name: Optional[str], title_hint: Optional[str]) -> bool:
    """Activate an existing window based on the process name/title clue."""
    hwnd = _best_existing_hwnd(exe_name, title_hint)
    if hwnd:
        _activate_hwnd(hwnd)
        return True
    return False
