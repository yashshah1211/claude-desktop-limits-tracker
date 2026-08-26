#!/usr/bin/env python3
"""
Claude Desktop Limits Tracker CLI for Windows
Displays 5-hour session limit and weekly limit status in the terminal.
"""

import sys
import os
import time
import argparse
import json

# Ensure UTF-8 output for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.claude_client import get_status

# ANSI Color codes for Windows terminal
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
BG_DARK = "\033[48;5;236m"

def render_bar(percent_left, width=28):
    """Renders a smooth color-coded progress bar for remaining limit."""
    percent_left = max(0.0, min(100.0, percent_left))
    filled_len = int(round(width * (percent_left / 100.0)))
    empty_len = width - filled_len

    if percent_left > 40:
        bar_color = GREEN
    elif percent_left > 15:
        bar_color = YELLOW
    else:
        bar_color = RED

    bar_str = bar_color + ("█" * filled_len) + DIM + ("░" * empty_len) + RESET
    return bar_str

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_dashboard(data):
    if not data.get("success"):
        print(f"\n{RED}{BOLD}[!] Error retrieving Claude limits:{RESET} {data.get('error', 'Unknown error')}")
        if data.get("suggestion"):
            print(f"{YELLOW}-> Suggestion:{RESET} {data['suggestion']}\n")
        return

    account = data.get("account", {})
    session_5h = data.get("session_5h", {})
    weekly = data.get("weekly", {})
    models = data.get("models", [])
    claude_running = data.get("claude_running", False)

    status_badge = f"{GREEN}● RUNNING{RESET}" if claude_running else f"{YELLOW}○ IDLE / CLOSED{RESET}"

    border = f"{CYAN}─" * 60 + RESET
    print(f"\n{border}")
    print(f" {BOLD}{MAGENTA}✦ CLAUDE.AI LIMITS TRACKER{RESET} {DIM}(Windows Desktop){RESET}")
    print(f" {DIM}Org:{RESET} {WHITE}{account.get('org_name', 'N/A')}{RESET}  |  {DIM}Tier:{RESET} {CYAN}{BOLD}{account.get('plan_tier', 'Free')}{RESET}  |  {status_badge}")
    print(border)

    # 1. 5-HOUR SESSION LIMIT
    s_left = session_5h.get("percent_left", 100.0)
    s_used = session_5h.get("percent_used", 0.0)
    s_human = session_5h.get("resets_in_human", "Full limit available")
    s_bar = render_bar(s_left, width=26)
    
    s_color = GREEN if s_left > 40 else (YELLOW if s_left > 15 else RED)

    print(f"\n {BOLD}1. Current Session Limit (5-Hour Rolling Window){RESET}")
    print(f"    Left:  {s_color}{BOLD}{s_left}%{RESET}  {s_bar}  {DIM}({s_used}% used){RESET}")
    print(f"    Reset: {CYAN}{s_human}{RESET}")
    if session_5h.get("resets_at"):
        print(f"    Time:  {DIM}{session_5h['resets_at']}{RESET}")

    # 2. WEEKLY LIMIT (7-DAY)
    w_left = weekly.get("percent_left", 100.0)
    w_used = weekly.get("percent_used", 0.0)
    w_human = weekly.get("resets_in_human", "Full limit available")
    w_bar = render_bar(w_left, width=26)

    w_color = GREEN if w_left > 40 else (YELLOW if w_left > 15 else RED)

    print(f"\n {BOLD}2. Weekly Limit (7-Day Rolling Window){RESET}")
    print(f"    Left:  {w_color}{BOLD}{w_left}%{RESET}  {w_bar}  {DIM}({w_used}% used){RESET}")
    print(f"    Reset: {CYAN}{w_human}{RESET}")
    if weekly.get("resets_at"):
        print(f"    Time:  {DIM}{weekly['resets_at']}{RESET}")

    # Scoped models if present (e.g. Sonnet, Opus)
    if models:
        print(f"\n {BOLD}3. Model-Specific Weekly Allocations{RESET}")
        for m in models:
            m_left = m.get("percent_left", 100.0)
            m_bar = render_bar(m_left, width=20)
            print(f"    • {WHITE}{m.get('name')}:{RESET} {m_left}% left {m_bar} {DIM}({m.get('resets_in_human')}){RESET}")

    print(f"\n{border}")
    print(f" {DIM}Last updated: {data.get('last_updated', 'Just now')}  •  Press Ctrl+C to exit{RESET}\n")

def main():
    parser = argparse.ArgumentParser(description="Claude.ai 5-Hour and Weekly Limit Tracker for Windows")
    parser.add_argument("--watch", "-w", type=int, nargs="?", const=60, default=None,
                        help="Live update mode. Optional interval in seconds (default: 60s)")
    parser.add_argument("--json", "-j", action="store_true", help="Output raw JSON data")
    parser.add_argument("--key", "-k", type=str, default=None, help="Manual sessionKey override")
    args = parser.parse_args()

    # Enable Windows Virtual Terminal Processing for ANSI colors
    if os.name == 'nt':
        try:
            kernel32 = ctypes.windll.kernel32
            hStdOut = kernel32.GetStdHandle(-11)
            mode = wintypes.DWORD()
            kernel32.GetConsoleMode(hStdOut, ctypes.byref(mode))
            kernel32.SetConsoleMode(hStdOut, mode.value | 0x0004)
        except Exception:
            pass

    if args.watch is not None:
        interval = max(5, args.watch)
        try:
            while True:
                clear_screen()
                data = get_status(manual_key=args.key)
                if args.json:
                    print(json.dumps(data, indent=2))
                else:
                    print_dashboard(data)
                    print(f"{DIM}Auto-refreshing every {interval} seconds...{RESET}")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nExiting watcher.")
            sys.exit(0)
    else:
        data = get_status(manual_key=args.key)
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print_dashboard(data)

if __name__ == "__main__":
    main()
