"""
Claude.ai Usage & Limits Harvester for Windows
Detects Claude Desktop session, retrieves 5-hour session limits and 7-day weekly limits.
"""

import os
import re
import sys
import json
import time
import base64
import ctypes
import urllib.parse
from datetime import datetime, timezone
from ctypes import wintypes
import requests
import psutil

# Strict outbound URL allowlist policy
ALLOWED_SCHEME = "https"
ALLOWED_HOSTNAME = "claude.ai"
SESSION_KEY_REGEX = re.compile(r'sk-ant-sid02-[A-Za-z0-9_\-]+')

def mask_session_key(key):
    """
    Safely redacts a session key, displaying only the first 8 and last 4 characters.
    Gracefully handles edge cases (None, empty string, strings < 12 chars) without IndexError.
    """
    if not key or not isinstance(key, str):
        return ""
    if len(key) < 12:
        return "*" * len(key)
    return f"{key[:8]}...{key[-4:]}"

def sanitize_error_message(msg, session_key=None):
    """
    Scrubs raw session keys or credential tokens from error messages and exception strings.
    Replaces matched tokens with their masked representation.
    """
    if not msg:
        return ""
    text = str(msg)
    if session_key and isinstance(session_key, str) and session_key in text:
        text = text.replace(session_key, mask_session_key(session_key))
    
    def _repl(match):
        return mask_session_key(match.group(0))
    
    return SESSION_KEY_REGEX.sub(_repl, text)

def safe_claude_get(url, headers=None, cookies=None, timeout=10):
    """
    Enforces that outbound HTTP requests strictly target https://claude.ai.
    Uses exact host parsing (urllib.parse) to reject attacker subdomains
    (e.g., https://claude.ai.attacker.com) and unencrypted HTTP schemes.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != ALLOWED_SCHEME or parsed.hostname != ALLOWED_HOSTNAME:
        raise ValueError(
            f"Security policy violation: Outbound requests are strictly restricted to "
            f"{ALLOWED_SCHEME}://{ALLOWED_HOSTNAME}. Blocked request to: {parsed.scheme}://{parsed.netloc}"
        )
    return requests.get(url, headers=headers, cookies=cookies, timeout=timeout)

# Win32 API setup for memory scanning
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

OpenProcess = ctypes.windll.kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE

ReadProcessMemory = ctypes.windll.kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [
    wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
]
ReadProcessMemory.restype = wintypes.BOOL

CloseHandle = ctypes.windll.kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL

VirtualQueryEx = ctypes.windll.kernel32.VirtualQueryEx

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("PartitionId", wintypes.WORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]

MEM_COMMIT = 0x1000
PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_WRITECOPY = 0x08
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80
PAGE_PROTECTION_MASK = 0xFF

def _is_readable_memory(protect):
    """True when a committed page's base protection permits reading."""
    return (protect & PAGE_PROTECTION_MASK) in (
        PAGE_READONLY, PAGE_READWRITE, PAGE_WRITECOPY,
        PAGE_EXECUTE_READ, PAGE_EXECUTE_READWRITE, PAGE_EXECUTE_WRITECOPY
    )

CLAUDE_PKG_PATH = os.path.expandvars(r"%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude")
CLAUDE_STANDARD_PATH = os.path.expandvars(r"%APPDATA%\Claude")

def get_claude_data_dir():
    if os.path.exists(CLAUDE_PKG_PATH):
        return CLAUDE_PKG_PATH
    if os.path.exists(CLAUDE_STANDARD_PATH):
        return CLAUDE_STANDARD_PATH
    return None

def is_claude_desktop_running():
    for p in psutil.process_iter(['name']):
        try:
            if 'claude' in (p.info['name'] or '').lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def scan_session_key_from_memory():
    """Scans running claude.exe processes for active sessionKey."""
    if ctypes.sizeof(ctypes.c_void_p) != 8:
        sys.stderr.write("[Memory Scanner] Skipping memory scan: 64-bit Python required.\n")
        return None

    try:
        claude_pids = []
        for p in psutil.process_iter(['pid', 'name']):
            try:
                if 'claude' in (p.info['name'] or '').lower():
                    claude_pids.append(p.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if not claude_pids:
            return None

        # Matches Claude session key tokens
        pattern = re.compile(rb'sk-ant-sid02-[A-Za-z0-9_\-]{80,}')
        
        for pid in claude_pids:
            try:
                h = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
            except Exception:
                continue
            if not h:
                continue
            
            mbi = MEMORY_BASIC_INFORMATION()
            addr = 0
            found_key = None
            
            try:
                while VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
                    if mbi.State == MEM_COMMIT and _is_readable_memory(mbi.Protect):
                        size = mbi.RegionSize
                        if size <= 10 * 1024 * 1024:
                            buf = ctypes.create_string_buffer(size)
                            bytes_read = ctypes.c_size_t()
                            if ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(bytes_read)):
                                matches = pattern.findall(buf.raw[:bytes_read.value])
                                if matches:
                                    found_key = matches[0].decode('ascii')
                                    break
                    addr += mbi.RegionSize
                    if addr >= 0x7FFFFFFFFFFF:
                        break
            finally:
                CloseHandle(h)

            if found_key:
                return found_key
                
        return None
    except PermissionError as e:
        sys.stderr.write(f"[Memory Scanner] Windows permission error accessing claude.exe: {e}\n")
        return None
    except Exception as e:
        # Gracefully handle Windows Defender / AV interference or OS errors without crashing
        clean_err = sanitize_error_message(str(e))
        sys.stderr.write(f"[Memory Scanner] Memory scan failed gracefully ({type(e).__name__}): {clean_err}\n")
        return None

def get_session_key_from_widget_config():
    """Fallback: Decrypts session key stored in widget config if available."""
    config_path = os.path.expandvars(r"%APPDATA%\claude-usage-widget\config.json")
    local_state_path = os.path.expandvars(r"%APPDATA%\claude-usage-widget\Local State")
    if not os.path.exists(config_path) or not os.path.exists(local_state_path):
        return None

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        class DATA_BLOB(ctypes.Structure):
            _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]

        CryptUnprotectData = ctypes.windll.crypt32.CryptUnprotectData
        CryptUnprotectData.argtypes = [
            ctypes.POINTER(DATA_BLOB), ctypes.POINTER(wintypes.LPWSTR),
            ctypes.POINTER(DATA_BLOB), wintypes.LPVOID, wintypes.LPVOID,
            wintypes.DWORD, ctypes.POINTER(DATA_BLOB)
        ]
        CryptUnprotectData.restype = wintypes.BOOL

        with open(local_state_path, 'r', encoding='utf-8') as f:
            local_state = json.load(f)
        enc_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
        if enc_key.startswith(b'DPAPI'):
            enc_key = enc_key[5:]
        
        in_blob = DATA_BLOB(len(enc_key), ctypes.create_string_buffer(enc_key, len(enc_key)))
        out_blob = DATA_BLOB()
        if not CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)):
            return None
        master_key = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)

        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        enc_str = cfg.get("sessionKey_encrypted", "")
        if not enc_str:
            return None
        raw = base64.b64decode(enc_str)
        if raw.startswith(b'v10'):
            nonce = raw[3:15]
            ciphertext = raw[15:]
            aesgcm = AESGCM(master_key)
            decrypted = aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted.decode('utf-8')
    except Exception:
        pass
    return None

_CACHED_SESSION_KEY = None

def _invalidate_session_key():
    """Clears the cached session key so the next call rescans for a fresh one."""
    global _CACHED_SESSION_KEY
    _CACHED_SESSION_KEY = None

def _find_custom_config_path():
    """Locates the optional plaintext claude_config.json beside the app.

    Resolves to the repository root when running from source and to the
    executable's directory when running as a PyInstaller build, falling
    back to the current working directory.
    """
    if getattr(sys, "frozen", False):
        candidate_dirs = [os.path.dirname(sys.executable)]
    else:
        candidate_dirs = [os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]
    candidate_dirs.append(os.getcwd())
    for d in candidate_dirs:
        p = os.path.join(d, "claude_config.json")
        if os.path.exists(p):
            return p
    return None

def get_session_key(manual_key=None):
    """Retrieves session key using memory scan, widget config, or manual override."""
    global _CACHED_SESSION_KEY
    if manual_key:
        return manual_key

    if _CACHED_SESSION_KEY:
        return _CACHED_SESSION_KEY

    # 1. Try memory scan from running claude.exe
    key = scan_session_key_from_memory()

    # 2. Try widget config fallback
    if not key:
        key = get_session_key_from_widget_config()

    # 3. Check custom local config if user saved one
    if not key:
        custom_cfg = _find_custom_config_path()
        if custom_cfg:
            try:
                with open(custom_cfg, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    if saved.get('sessionKey'):
                        key = saved['sessionKey']
            except Exception:
                pass

    if key:
        _CACHED_SESSION_KEY = key
    return key

def get_headers_and_cookies(session_key):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://claude.ai/",
        "Origin": "https://claude.ai"
    }
    cookies = {
        "sessionKey": session_key
    }
    return headers, cookies

def get_primary_organization(session_key):
    """Fetches user organizations and returns the primary chat org."""
    headers, cookies = get_headers_and_cookies(session_key)
    try:
        r = safe_claude_get("https://claude.ai/api/organizations", headers=headers, cookies=cookies, timeout=10)
        if r.status_code in (401, 403):
            _invalidate_session_key()
        if r.status_code != 200:
            return None, f"API returned status {r.status_code}"
        orgs = r.json()
        if not isinstance(orgs, list) or not orgs:
            return None, "No organizations found"
            
        # Priority: org with 'chat' capability
        chat_orgs = [o for o in orgs if 'chat' in o.get('capabilities', [])]
        selected = chat_orgs[0] if chat_orgs else orgs[0]
        return selected, None
    except Exception as e:
        return None, sanitize_error_message(str(e), session_key)

def get_organization_details(session_key, org_id):
    """Fetches org metadata such as rate_limit_tier."""
    headers, cookies = get_headers_and_cookies(session_key)
    try:
        r = safe_claude_get(f"https://claude.ai/api/organizations/{org_id}", headers=headers, cookies=cookies, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}

def get_raw_usage(session_key, org_id):
    """Fetches live raw usage from Claude.ai API."""
    headers, cookies = get_headers_and_cookies(session_key)
    try:
        r = safe_claude_get(f"https://claude.ai/api/organizations/{org_id}/usage", headers=headers, cookies=cookies, timeout=10)
        if r.status_code in (401, 403):
            _invalidate_session_key()
        if r.status_code == 200:
            return r.json(), None
        return None, f"Usage API returned status {r.status_code}"
    except Exception as e:
        return None, sanitize_error_message(str(e), session_key)

def get_local_history(limit=50):
    """Reads usage history samples recorded by Claude Desktop."""
    data_dir = get_claude_data_dir()
    if not data_dir:
        return []
    history_file = os.path.join(data_dir, "plan-usage-history.json")
    if not os.path.exists(history_file):
        return []

    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        samples = data.get("samples", [])
        formatted = []
        for s in samples[-limit:]:
            t = s.get('t', 0)
            u = s.get('u', {})
            formatted.append({
                "timestamp": t,
                "datetime": datetime.fromtimestamp(t / 1000.0, tz=timezone.utc).isoformat() if t else None,
                "session_5h_used": u.get('fh', 0),
                "weekly_used": u.get('sd', 0)
            })
        return formatted
    except Exception:
        return []

_CACHED_FREE_TIER_COOLDOWN = None
_COOLDOWN_CACHE_FILE = os.path.expandvars(r"%LOCALAPPDATA%\ClaudeLimitTracker\cooldown_state.json")
COOLDOWN_MEM_PATTERN = re.compile(rb'\{[^{}]*?"resetsAt":\s*(\d+)[^{}]*?"utilization":\s*([0-9.]+)[^{}]*?\}')

def _load_persisted_cooldown():
    """Loads non-sensitive cooldown metadata from local disk cache if valid and unexpired."""
    if not os.path.exists(_COOLDOWN_CACHE_FILE):
        return None
    try:
        with open(_COOLDOWN_CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("resetsAt", 0) > time.time():
            return {
                "resetsAt": data["resetsAt"],
                "utilization": float(data.get("utilization", 0.0)),
                "observedAt": float(data.get("observedAt", 0.0)),
                "atWall": bool(data.get("atWall", False))
            }
    except Exception:
        pass
    return None

def _save_persisted_cooldown(record):
    """Safely saves non-sensitive cooldown metadata (zero credentials)."""
    if not record or not isinstance(record, dict):
        return
    try:
        os.makedirs(os.path.dirname(_COOLDOWN_CACHE_FILE), exist_ok=True)
        payload = {
            "resetsAt": record.get("resetsAt"),
            "utilization": record.get("utilization"),
            "observedAt": record.get("observedAt"),
            "atWall": record.get("atWall", False)
        }
        with open(_COOLDOWN_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(payload, f)
    except Exception:
        pass

def scan_free_tier_cooldown_from_memory():
    """Scans running claude.exe processes for live, uncompressed ochre_heron_tide cooldown record."""
    if ctypes.sizeof(ctypes.c_void_p) != 8:
        return None

    try:
        claude_pids = []
        for p in psutil.process_iter(['pid', 'name']):
            try:
                if 'claude' in (p.info['name'] or '').lower():
                    claude_pids.append(p.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if not claude_pids:
            return None

        best = None
        now = time.time()
        for pid in claude_pids:
            try:
                h = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
            except Exception:
                continue
            if not h:
                continue

            mbi = MEMORY_BASIC_INFORMATION()
            addr = 0
            try:
                while VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
                    if mbi.State == MEM_COMMIT and _is_readable_memory(mbi.Protect):
                        size = mbi.RegionSize
                        if size <= 10 * 1024 * 1024:
                            buf = ctypes.create_string_buffer(size)
                            bytes_read = ctypes.c_size_t()
                            if ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(bytes_read)):
                                raw = buf.raw[:bytes_read.value]
                                if b'resetsAt' in raw and b'utilization' in raw:
                                    for m in COOLDOWN_MEM_PATTERN.finditer(raw):
                                        try:
                                            obj = json.loads(m.group(0).decode('utf-8'))
                                            r_at = obj.get('resetsAt')
                                            if r_at and r_at > now:
                                                if not best or obj.get('observedAt', 0) > best.get('observedAt', 0):
                                                    best = obj
                                        except Exception:
                                            pass
                    addr += mbi.RegionSize
                    if addr >= 0x7FFFFFFFFFFF:
                        break
            finally:
                CloseHandle(h)
        return best
    except Exception:
        return None

def get_free_tier_cooldown():
    """
    Reads active free tier message cooldown and utilization from Claude Desktop.
    Uses a resilient multi-layered approach to prevent false 100% resets:
    1. Disk scan of LevelDB write-ahead logs (.log prioritized over compacted .ldb)
    2. Process memory scan of running claude.exe (uncompressed, live)
    3. Active in-memory and persistent cooldown cache fallback
    """
    global _CACHED_FREE_TIER_COOLDOWN
    now = time.time()
    best_record = None

    # 1. First check LevelDB disk files (uncompressed .log files take priority)
    data_dir = get_claude_data_dir()
    if data_dir:
        leveldb_dir = os.path.join(data_dir, "Local Storage", "leveldb")
        if os.path.exists(leveldb_dir):
            try:
                filenames = sorted(os.listdir(leveldb_dir), key=lambda x: (not x.endswith('.log'), x))
                pattern = re.compile(rb'\{"resetsAt":\s*(\d+)[^\}]*\}')
                for fn in filenames:
                    if fn.endswith(('.log', '.ldb')):
                        fp = os.path.join(leveldb_dir, fn)
                        try:
                            with open(fp, 'rb') as f:
                                content = f.read()
                            for m in pattern.finditer(content):
                                try:
                                    obj = json.loads(m.group(0).decode('utf-8', errors='ignore'))
                                    resets_at = obj.get('resetsAt')
                                    if resets_at and resets_at > now:
                                        if not best_record or obj.get('observedAt', 0) > best_record.get('observedAt', 0):
                                            best_record = obj
                                except Exception:
                                    pass
                        except Exception:
                            pass
            except Exception:
                pass

    # 2. If disk scan didn't find a record (e.g. during compaction), scan running process memory
    if not best_record and is_claude_desktop_running():
        mem_rec = scan_free_tier_cooldown_from_memory()
        if mem_rec:
            best_record = mem_rec

    # 3. Update memory and disk caches if a valid record was discovered
    if best_record:
        if not _CACHED_FREE_TIER_COOLDOWN or best_record.get('observedAt', 0) >= _CACHED_FREE_TIER_COOLDOWN.get('observedAt', 0):
            _CACHED_FREE_TIER_COOLDOWN = best_record
            _save_persisted_cooldown(best_record)
        return best_record

    # 4. Fallback to active in-memory cache if resetsAt is still in the future
    if _CACHED_FREE_TIER_COOLDOWN and _CACHED_FREE_TIER_COOLDOWN.get('resetsAt', 0) > now:
        return _CACHED_FREE_TIER_COOLDOWN

    # 5. Fallback to persistent disk cache if app/process was restarted
    persisted = _load_persisted_cooldown()
    if persisted and persisted.get('resetsAt', 0) > now:
        _CACHED_FREE_TIER_COOLDOWN = persisted
        return persisted

    # Cooldown has truly elapsed
    _CACHED_FREE_TIER_COOLDOWN = None
    return None

def _parse_resets_at(value):
    """Parses a resets_at value into a tz-aware UTC datetime.

    Accepts ISO-8601 strings (with or without a timezone offset) and
    Unix epoch timestamps given in seconds or milliseconds.
    Returns None when the value cannot be parsed.
    """
    if value is None or value == "":
        return None

    if isinstance(value, (int, float)):
        ts = float(value)
        if abs(ts) > 1e12:
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None

    text = str(value).strip()

    # Numeric epoch string (seconds or milliseconds)
    try:
        ts = float(text)
        if abs(ts) > 1e12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        pass

    # ISO-8601 string
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00", 1))
    except (ValueError, TypeError):
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def format_time_remaining(resets_at_iso):
    """Calculates human readable countdown to resets_at."""
    resets_dt = _parse_resets_at(resets_at_iso)
    if resets_dt is None:
        return None, "Full limit available" if not resets_at_iso else str(resets_at_iso)

    try:
        local_dt = resets_dt.astimezone()
        time_str = local_dt.strftime("%I:%M %p").lstrip("0")
        now = datetime.now(timezone.utc)
        diff = resets_dt - now
        total_seconds = int(diff.total_seconds())

        if total_seconds <= 0:
            return 0, "Resets now"

        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if days > 0:
            human = f"{days}d {hours}h left (until {time_str})"
        elif hours > 0:
            human = f"{hours}h {minutes}m left (until {time_str})"
        elif minutes > 0:
            human = f"{minutes}m {seconds}s left (until {time_str})"
        else:
            human = f"{seconds}s left"

        return total_seconds, human
    except Exception:
        return None, str(resets_at_iso)

def parse_tier_name(tier_str, billing_type=None):
    if not tier_str:
        return "Free"
    t = tier_str.lower()
    if "pro" in t:
        return "Pro"
    if "max" in t:
        return "Max"
    if "team" in t or "enterprise" in t or "raven" in t:
        return "Team"
    if "default" in t or t == "free":
        return "Free"
    return tier_str.replace("_", " ").title()

def get_status(manual_key=None):
    """
    Main aggregator function.
    Returns normalized status containing:
    - 5-hour limit (% used, % left, resets_at, countdown)
    - Weekly limit (% used, % left, resets_at, countdown)
    - Claude Desktop process status
    - Account details & Tier
    - Scoped model limits if available
    - Historical trends
    """
    claude_running = is_claude_desktop_running()
    session_key = get_session_key(manual_key)

    if not session_key:
        return {
            "success": False,
            "error": "Claude Desktop is not running or no active session found.",
            "claude_running": claude_running,
            "suggestion": "Please open Claude Desktop or provide your session key."
        }

    org, err = get_primary_organization(session_key)
    if err or not org:
        return {
            "success": False,
            "error": sanitize_error_message(f"Failed to get organization: {err}", session_key),
            "claude_running": claude_running
        }

    org_id = org.get("uuid")
    org_name = org.get("name", "My Organization")
    
    org_details = get_organization_details(session_key, org_id)
    plan_tier = parse_tier_name(
        org_details.get("rate_limit_tier") or org.get("rate_limit_tier"),
        org_details.get("billing_type")
    )

    usage_data, err = get_raw_usage(session_key, org_id)
    if err or not usage_data:
        return {
            "success": False,
            "error": sanitize_error_message(f"Failed to retrieve usage data: {err}", session_key),
            "claude_running": claude_running,
            "account": {
                "org_id": org_id,
                "org_name": org_name,
                "plan_tier": plan_tier
            }
        }

    # Extract 5-hour session limit
    session_used = 0.0
    session_resets_at = None

    if usage_data.get("five_hour") and isinstance(usage_data["five_hour"], dict):
        fh = usage_data["five_hour"]
        session_used = float(fh.get("utilization") or 0.0)
        session_resets_at = fh.get("resets_at")

    # Extract weekly limit
    weekly_used = 0.0
    weekly_resets_at = None

    if usage_data.get("seven_day") and isinstance(usage_data["seven_day"], dict):
        sd = usage_data["seven_day"]
        weekly_used = float(sd.get("utilization") or 0.0)
        weekly_resets_at = sd.get("resets_at")

    # Look inside limits[] array if present (newer Anthropic API schema)
    scoped_models = []
    limits_arr = usage_data.get("limits") or []
    if isinstance(limits_arr, list):
        for lim in limits_arr:
            kind = lim.get("kind")
            pct = float(lim.get("percent") or 0.0)
            res = lim.get("resets_at")
            if kind == "session":
                session_used = max(session_used, pct)
                if not session_resets_at and res:
                    session_resets_at = res
            elif kind == "weekly_all":
                weekly_used = max(weekly_used, pct)
                if not weekly_resets_at and res:
                    weekly_resets_at = res
            elif kind == "weekly_scoped":
                model_name = lim.get("scope", {}).get("model", {}).get("display_name", "Model")
                rem_sec, rem_h = format_time_remaining(res)
                scoped_models.append({
                    "name": model_name,
                    "percent_used": round(pct, 1),
                    "percent_left": round(max(0.0, 100.0 - pct), 1),
                    "resets_at": res,
                    "resets_in_human": rem_h
                })

    # Calculations for 5-Hour Session
    session_left = round(max(0.0, 100.0 - session_used), 1)
    session_rem_sec, session_rem_human = format_time_remaining(session_resets_at)
    
    if session_used >= 90:
        session_status = "danger"
    elif session_used >= 70:
        session_status = "warning"
    else:
        session_status = "normal"

    # Check for active Free Tier Cooldown / message rate limit from Claude Desktop's local state
    free_cooldown = get_free_tier_cooldown()
    if free_cooldown:
        resets_at_ts = free_cooldown.get("resetsAt")
        now_ts = time.time()
        if resets_at_ts and resets_at_ts > now_ts:
            resets_dt = datetime.fromtimestamp(resets_at_ts, tz=timezone.utc)
            local_dt = resets_dt.astimezone()
            time_str = local_dt.strftime("%I:%M %p").lstrip("0")
            diff_sec = int(resets_at_ts - now_ts)
            h = diff_sec // 3600
            m = (diff_sec % 3600) // 60
            s = diff_sec % 60
            countdown_str = f"{h}h {m}m" if h > 0 else f"{m}m {s}s"

            raw_util = float(free_cooldown.get("utilization", 1.0))
            session_used = min(100.0, round(raw_util * 100.0, 1))
            session_left = round(max(0.0, 100.0 - session_used), 1)
            session_resets_at = resets_dt.isoformat()
            session_rem_sec = diff_sec

            at_wall = bool(free_cooldown.get("atWall")) or session_used >= 100.0
            if at_wall:
                session_rem_human = f"Out of free messages until {time_str} ({countdown_str} left)"
                session_status = "danger"
            else:
                session_rem_human = f"{countdown_str} left (until {time_str})"
                if session_used >= 90:
                    session_status = "danger"
                elif session_used >= 70:
                    session_status = "warning"
                else:
                    session_status = "normal"

    # Calculations for Weekly Limit
    weekly_left = round(max(0.0, 100.0 - weekly_used), 1)
    weekly_rem_sec, weekly_rem_human = format_time_remaining(weekly_resets_at)

    if weekly_used >= 90:
        weekly_status = "danger"
    elif weekly_used >= 70:
        weekly_status = "warning"
    else:
        weekly_status = "normal"

    if plan_tier == "Free" and not weekly_resets_at:
        weekly_rem_human = "Free tier (5h session governed)"
        weekly_status = "normal"

    history = get_local_history(limit=25)

    return {
        "success": True,
        "claude_running": claude_running,
        "account": {
            "org_id": org_id,
            "org_name": org_name,
            "plan_tier": plan_tier
        },
        "session_5h": {
            "percent_used": round(session_used, 1),
            "percent_left": session_left,
            "resets_at": session_resets_at,
            "resets_in_seconds": session_rem_sec,
            "resets_in_human": session_rem_human,
            "status": session_status
        },
        "weekly": {
            "percent_used": round(weekly_used, 1),
            "percent_left": weekly_left,
            "resets_at": weekly_resets_at,
            "resets_in_seconds": weekly_rem_sec,
            "resets_in_human": weekly_rem_human,
            "status": weekly_status
        },
        "models": scoped_models,
        "history": history,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    status = get_status()
    print(json.dumps(status, indent=2))
