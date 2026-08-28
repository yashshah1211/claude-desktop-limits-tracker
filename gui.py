"""
Claude Desktop Limits Tracker - Native Windows Desktop GUI
Real-time display of 5-hour session limit and weekly limit for Claude.ai on Windows.
"""

import sys
import os
import time
import math
import threading
import queue
import json
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, messagebox

# Reconfigure stdout for UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add workspace to path
sys.path.insert(0, os.path.dirname(__file__))
from src.claude_client import get_status, sanitize_error_message

# High DPI awareness for crisp rendering on modern Windows screens
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per-monitor DPI aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Palette (Claude Anthropic inspired dark theme)
BG_DARK = "#121214"
BG_CARD = "#1c1c20"
BG_CARD_HOVER = "#242429"
BORDER_COLOR = "#2e2e34"
TEXT_PRIMARY = "#f4f4f5"
TEXT_SECONDARY = "#a1a1aa"
TEXT_MUTED = "#71717a"

COLOR_CORAL = "#da7756"
COLOR_ACCENT = "#e07a5f"
COLOR_GREEN = "#10b981"
COLOR_YELLOW = "#f59e0b"
COLOR_RED = "#ef4444"
COLOR_CYAN = "#06b6d4"

class RadialGauge(tk.Canvas):
    """Custom high-DPI anti-aliased circular progress gauge."""
    def __init__(self, parent, title, subtitle="", size=190, **kwargs):
        super().__init__(parent, width=size, height=size, bg=BG_CARD, highlightthickness=0, **kwargs)
        self.size = size
        self.title = title
        self.subtitle = subtitle
        self.percent_left = 100.0
        self.percent_used = 0.0
        self.status_text = "Full limit available"
        self.center = size // 2
        self.radius = (size // 2) - 18
        self.width = 12
        self.draw()

    def update_data(self, percent_left, percent_used, status_text):
        self.percent_left = max(0.0, min(100.0, float(percent_left)))
        self.percent_used = max(0.0, min(100.0, float(percent_used)))
        self.status_text = status_text
        self.draw()

    def get_color(self):
        if self.percent_left > 40:
            return COLOR_GREEN
        elif self.percent_left > 15:
            return COLOR_YELLOW
        else:
            return COLOR_RED

    def draw(self):
        self.delete("all")
        c = self.center
        r = self.radius
        w = self.width

        # Background track arc
        bbox = [c - r, c - r, c + r, c + r]
        self.create_arc(bbox, start=0, extent=359.99, outline="#27272e", width=w, style="arc")

        # Active progress arc (starting at 90 deg = 12 o'clock, clockwise)
        extent = -(self.percent_left / 100.0) * 359.99
        gauge_color = self.get_color()
        if self.percent_left > 0:
            self.create_arc(bbox, start=90, extent=extent, outline=gauge_color, width=w, style="arc")

        # Center text: Percentage Left
        self.create_text(
            c, c - 18,
            text=f"{self.percent_left:.0f}%",
            fill=TEXT_PRIMARY,
            font=("Segoe UI", 26, "bold")
        )
        self.create_text(
            c, c + 12,
            text="REMAINING",
            fill=TEXT_MUTED,
            font=("Segoe UI", 8, "bold")
        )
        
        # Used subtitle below percentage
        self.create_text(
            c, c + 32,
            text=f"({self.percent_used:.1f}% used)",
            fill=TEXT_SECONDARY,
            font=("Segoe UI", 9)
        )

class ClaudeTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Claude.ai Limits Tracker - Windows")
        self.root.geometry("640x700")
        self.root.minsize(580, 620)
        self.root.configure(bg=BG_DARK)

        # Set Window Icon
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
        icon_file = os.path.join(base_dir, "assets", "icon.ico")
        if os.path.exists(icon_file):
            try:
                self.root.iconbitmap(icon_file)
            except Exception:
                pass

        # State
        self.always_on_top = False
        self.auto_refresh = True
        self.refresh_seconds = 60
        self.countdown_remaining = self.refresh_seconds
        self.is_refreshing = False
        self.ui_queue = queue.Queue()
        self.last_data = None
        self.history_visible = False

        self.build_ui()
        self.trigger_refresh()
        self.start_timer_loop()

    def build_ui(self):
        # 1. Header Bar
        header = tk.Frame(self.root, bg=BG_DARK, padx=20, pady=16)
        header.pack(fill="x")

        # App Title & Icon
        title_box = tk.Frame(header, bg=BG_DARK)
        title_box.pack(side="left")

        app_title = tk.Label(
            title_box,
            text="✦ Claude.ai Limits Tracker",
            fg=COLOR_CORAL,
            bg=BG_DARK,
            font=("Segoe UI", 16, "bold")
        )
        app_title.pack(anchor="w")

        self.lbl_subtitle = tk.Label(
            title_box,
            text="Detecting Claude Desktop...",
            fg=TEXT_SECONDARY,
            bg=BG_DARK,
            font=("Segoe UI", 9)
        )
        self.lbl_subtitle.pack(anchor="w", pady=(2, 0))

        # Top Control Buttons (Always on Top, Refresh)
        btn_box = tk.Frame(header, bg=BG_DARK)
        btn_box.pack(side="right")

        self.btn_pin = tk.Button(
            btn_box,
            text="📌 Pin on Top",
            command=self.toggle_always_on_top,
            bg=BG_CARD,
            fg=TEXT_SECONDARY,
            activebackground=BG_CARD_HOVER,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        )
        self.btn_pin.pack(side="left", padx=4)

        self.btn_refresh = tk.Button(
            btn_box,
            text="↻ Refresh",
            command=self.trigger_refresh,
            bg=COLOR_CORAL,
            fg="#ffffff",
            activebackground="#c76848",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=14,
            pady=6,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        )
        self.btn_refresh.pack(side="left", padx=4)

        # Status Ribbon (Org, Tier, Claude status)
        ribbon = tk.Frame(self.root, bg=BORDER_COLOR, padx=1, pady=1)
        ribbon.pack(fill="x", padx=20, pady=(0, 16))

        ribbon_inner = tk.Frame(ribbon, bg=BG_CARD, padx=16, pady=10)
        ribbon_inner.pack(fill="x")

        self.lbl_running_badge = tk.Label(
            ribbon_inner,
            text="● Claude Desktop Running",
            fg=COLOR_GREEN,
            bg=BG_CARD,
            font=("Segoe UI", 9, "bold")
        )
        self.lbl_running_badge.pack(side="left")

        self.lbl_tier_badge = tk.Label(
            ribbon_inner,
            text="Plan: Free",
            fg=COLOR_CYAN,
            bg=BG_CARD,
            font=("Segoe UI", 9, "bold")
        )
        self.lbl_tier_badge.pack(side="right")

        self.lbl_org_badge = tk.Label(
            ribbon_inner,
            text="Org: Connecting...",
            fg=TEXT_SECONDARY,
            bg=BG_CARD,
            font=("Segoe UI", 9)
        )
        self.lbl_org_badge.pack(side="right", padx=16)

        # 2. Main Gauges Container (Cards side by side)
        gauges_frame = tk.Frame(self.root, bg=BG_DARK, padx=20)
        gauges_frame.pack(fill="x", pady=4)

        # Left Card: 5-Hour Session Limit
        card_session = tk.Frame(gauges_frame, bg=BORDER_COLOR, padx=1, pady=1)
        card_session.pack(side="left", fill="both", expand=True, padx=(0, 8))

        inner_session = tk.Frame(card_session, bg=BG_CARD, padx=14, pady=14)
        inner_session.pack(fill="both", expand=True)

        lbl_s_title = tk.Label(
            inner_session,
            text="CURRENT SESSION",
            fg=TEXT_MUTED,
            bg=BG_CARD,
            font=("Segoe UI", 9, "bold")
        )
        lbl_s_title.pack()

        lbl_s_sub = tk.Label(
            inner_session,
            text="Rolling 5-Hour Limit",
            fg=TEXT_PRIMARY,
            bg=BG_CARD,
            font=("Segoe UI", 12, "bold")
        )
        lbl_s_sub.pack(pady=(2, 6))

        self.gauge_session = RadialGauge(inner_session, "Session Limit", size=180)
        self.gauge_session.pack(pady=4)

        self.lbl_session_reset = tk.Label(
            inner_session,
            text="Full limit available",
            fg=COLOR_GREEN,
            bg=BG_CARD,
            font=("Segoe UI", 10, "bold"),
            wraplength=240,
            justify="center"
        )
        self.lbl_session_reset.pack(pady=(4, 2))

        self.lbl_session_detail = tk.Label(
            inner_session,
            text="Resets automatically 5h after prompt",
            fg=TEXT_MUTED,
            bg=BG_CARD,
            font=("Segoe UI", 8),
            wraplength=240,
            justify="center"
        )
        self.lbl_session_detail.pack()

        # Right Card: Weekly Limit
        card_weekly = tk.Frame(gauges_frame, bg=BORDER_COLOR, padx=1, pady=1)
        card_weekly.pack(side="right", fill="both", expand=True, padx=(8, 0))

        inner_weekly = tk.Frame(card_weekly, bg=BG_CARD, padx=14, pady=14)
        inner_weekly.pack(fill="both", expand=True)

        lbl_w_title = tk.Label(
            inner_weekly,
            text="WEEKLY LIMIT",
            fg=TEXT_MUTED,
            bg=BG_CARD,
            font=("Segoe UI", 9, "bold")
        )
        lbl_w_title.pack()

        lbl_w_sub = tk.Label(
            inner_weekly,
            text="7-Day Rolling Quota",
            fg=TEXT_PRIMARY,
            bg=BG_CARD,
            font=("Segoe UI", 12, "bold")
        )
        lbl_w_sub.pack(pady=(2, 6))

        self.gauge_weekly = RadialGauge(inner_weekly, "Weekly Limit", size=180)
        self.gauge_weekly.pack(pady=4)

        self.lbl_weekly_reset = tk.Label(
            inner_weekly,
            text="Full limit available",
            fg=COLOR_GREEN,
            bg=BG_CARD,
            font=("Segoe UI", 10, "bold"),
            wraplength=240,
            justify="center"
        )
        self.lbl_weekly_reset.pack(pady=(4, 2))

        self.lbl_weekly_detail = tk.Label(
            inner_weekly,
            text="All models combined limit",
            fg=TEXT_MUTED,
            bg=BG_CARD,
            font=("Segoe UI", 8),
            wraplength=240,
            justify="center"
        )
        self.lbl_weekly_detail.pack()

        # 3. Model Breakdown & Quick Tips
        self.models_container = tk.Frame(self.root, bg=BG_DARK, padx=20, pady=12)
        self.models_container.pack(fill="x")

        # 4. Usage History Drawer (Expandable)
        history_toggle_frame = tk.Frame(self.root, bg=BG_DARK, padx=20)
        history_toggle_frame.pack(fill="x", pady=(4, 0))

        self.btn_history_toggle = tk.Button(
            history_toggle_frame,
            text="▼ Show Usage History & Trends",
            command=self.toggle_history,
            bg=BG_DARK,
            fg=TEXT_SECONDARY,
            activebackground=BG_DARK,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        )
        self.btn_history_toggle.pack(anchor="w")

        self.history_frame = tk.Frame(self.root, bg=BG_CARD, padx=16, pady=12)
        # Hidden by default

        self.history_canvas = tk.Canvas(self.history_frame, bg=BG_CARD, height=120, highlightthickness=0)
        self.history_canvas.pack(fill="both", expand=True)

        # 5. Footer Bar (Status / Next Refresh)
        footer = tk.Frame(self.root, bg=BG_DARK, padx=20, pady=12)
        footer.pack(side="bottom", fill="x")

        self.lbl_footer = tk.Label(
            footer,
            text="Auto-refreshing in 60s",
            fg=TEXT_MUTED,
            bg=BG_DARK,
            font=("Segoe UI", 9)
        )
        self.lbl_footer.pack(side="left")

        lbl_author = tk.Label(
            footer,
            text="Strictly Claude Desktop Windows",
            fg=TEXT_MUTED,
            bg=BG_DARK,
            font=("Segoe UI", 8)
        )
        lbl_author.pack(side="right")

    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.root.attributes("-topmost", self.always_on_top)
        if self.always_on_top:
            self.btn_pin.configure(bg=COLOR_CORAL, fg="#ffffff", text="📌 Pinned")
        else:
            self.btn_pin.configure(bg=BG_CARD, fg=TEXT_SECONDARY, text="📌 Pin on Top")

    def toggle_history(self):
        self.history_visible = not self.history_visible
        if self.history_visible:
            self.history_frame.pack(fill="x", padx=20, pady=(6, 12))
            self.btn_history_toggle.configure(text="▲ Hide Usage History")
            self.render_history_chart()
        else:
            self.history_frame.pack_forget()
            self.btn_history_toggle.configure(text="▼ Show Usage History & Trends")

    def render_history_chart(self):
        self.history_canvas.delete("all")
        if not self.last_data or not self.last_data.get("history"):
            self.history_canvas.create_text(
                200, 60,
                text="No local history samples recorded yet.",
                fill=TEXT_MUTED,
                font=("Segoe UI", 9)
            )
            return

        samples = self.last_data["history"][-20:]
        w = self.history_canvas.winfo_width() or 560
        h = 110

        # Draw axis lines
        self.history_canvas.create_line(10, h - 20, w - 10, h - 20, fill=BORDER_COLOR)
        
        step_x = max(10, (w - 40) / max(1, len(samples) - 1))
        
        pts_session = []
        pts_weekly = []
        
        for i, s in enumerate(samples):
            x = 20 + i * step_x
            # Peak used
            s_val = s.get("session_5h_used", 0)
            w_val = s.get("weekly_used", 0)
            
            y_s = (h - 25) - (s_val / 100.0) * (h - 45)
            y_w = (h - 25) - (w_val / 100.0) * (h - 45)
            
            pts_session.extend([x, y_s])
            pts_weekly.extend([x, y_w])

            # Draw small dots
            self.history_canvas.create_oval(x - 2, y_s - 2, x + 2, y_s + 2, fill=COLOR_CORAL, outline="")

        if len(pts_session) >= 4:
            self.history_canvas.create_line(pts_session, fill=COLOR_CORAL, width=2, smooth=True)

        # Legend
        self.history_canvas.create_text(
            40, 12, text="― Session Usage %", fill=COLOR_CORAL, font=("Segoe UI", 8, "bold"), anchor="w"
        )

    def trigger_refresh(self):
        if self.is_refreshing:
            return
        self.is_refreshing = True
        self.countdown_remaining = self.refresh_seconds
        self.btn_refresh.configure(state="disabled", text="Refreshing...")
        self.lbl_footer.configure(text="Fetching latest usage from Claude.ai...")

        def worker():
            try:
                data = get_status()
            except Exception as e:
                data = {"success": False, "error": sanitize_error_message(str(e))}
            self.ui_queue.put(data)

        threading.Thread(target=worker, daemon=True).start()

    def process_queue(self):
        """Drains pending results and applies them on the Tk main thread."""
        while True:
            try:
                data = self.ui_queue.get_nowait()
            except queue.Empty:
                return
            self.update_display(data)

    def update_display(self, data):
        self.is_refreshing = False
        self.btn_refresh.configure(state="normal", text="↻ Refresh")
        self.last_data = data

        if not data.get("success"):
            err = sanitize_error_message(data.get("error", "Unknown error"))
            self.lbl_subtitle.configure(text=f"Error: {err}", fg=COLOR_RED)
            self.lbl_running_badge.configure(text="○ Claude Offline", fg=COLOR_YELLOW)
            return

        account = data.get("account", {})
        session_5h = data.get("session_5h", {})
        weekly = data.get("weekly", {})
        models = data.get("models", [])
        claude_running = data.get("claude_running", False)

        # Header info
        self.lbl_subtitle.configure(
            text=f"Connected to {account.get('org_name', 'Personal Account')}",
            fg=TEXT_SECONDARY
        )
        
        if claude_running:
            self.lbl_running_badge.configure(text="● Claude Desktop Running", fg=COLOR_GREEN)
        else:
            self.lbl_running_badge.configure(text="○ Claude Closed (Cached Session)", fg=COLOR_YELLOW)

        tier = account.get("plan_tier", "Free")
        self.lbl_tier_badge.configure(text=f"Plan: {tier}")
        self.lbl_org_badge.configure(text=f"Org: {account.get('org_id', '')[:8]}...")

        # 1. Update 5-Hour Session Limit
        s_left = session_5h.get("percent_left", 100.0)
        s_used = session_5h.get("percent_used", 0.0)
        s_human = session_5h.get("resets_in_human", "Full limit available")
        self.gauge_session.update_data(s_left, s_used, s_human)
        self.lbl_session_reset.configure(text=s_human, fg=self.gauge_session.get_color())
        
        if session_5h.get("resets_at"):
            try:
                dt = datetime.fromisoformat(session_5h["resets_at"].replace("Z", "+00:00")).astimezone()
                time_str = dt.strftime("%I:%M %p").lstrip("0")
                self.lbl_session_detail.configure(text=f"Resets at {time_str} ({session_5h['resets_at'][:10]})")
            except Exception:
                self.lbl_session_detail.configure(text=session_5h.get("resets_at"))
        else:
            self.lbl_session_detail.configure(text="No active prompt cooldown")

        # 2. Update Weekly Limit
        w_left = weekly.get("percent_left", 100.0)
        w_used = weekly.get("percent_used", 0.0)
        w_human = weekly.get("resets_in_human", "Full limit available")
        self.gauge_weekly.update_data(w_left, w_used, w_human)
        self.lbl_weekly_reset.configure(text=w_human, fg=self.gauge_weekly.get_color())

        if weekly.get("resets_at"):
            try:
                dt = datetime.fromisoformat(weekly["resets_at"].replace("Z", "+00:00")).astimezone()
                date_str = dt.strftime("%a %b %d, %I:%M %p")
                self.lbl_weekly_detail.configure(text=f"Resets on {date_str}")
            except Exception:
                self.lbl_weekly_detail.configure(text=weekly.get("resets_at"))
        else:
            self.lbl_weekly_detail.configure(text="All models 7-day limit")

        # 3. Model breakdown
        for child in self.models_container.winfo_children():
            child.destroy()

        if models:
            m_header = tk.Label(
                self.models_container, text="MODEL-SPECIFIC WEEKLY LIMITS",
                fg=TEXT_MUTED, bg=BG_DARK, font=("Segoe UI", 9, "bold")
            )
            m_header.pack(anchor="w", pady=(0, 6))

            for m in models:
                row = tk.Frame(self.models_container, bg=BG_CARD, padx=12, pady=8)
                row.pack(fill="x", pady=2)

                m_name = tk.Label(row, text=m.get("name", "Model"), fg=TEXT_PRIMARY, bg=BG_CARD, font=("Segoe UI", 9, "bold"))
                m_name.pack(side="left")

                m_pct = tk.Label(row, text=f"{m.get('percent_left')}% left", fg=COLOR_GREEN, bg=BG_CARD, font=("Segoe UI", 9, "bold"))
                m_pct.pack(side="right")

                m_reset = tk.Label(row, text=m.get("resets_in_human", ""), fg=TEXT_MUTED, bg=BG_CARD, font=("Segoe UI", 8))
                m_reset.pack(side="right", padx=12)

        if self.history_visible:
            self.render_history_chart()

        self.lbl_footer.configure(text=f"Updated just now  •  Next check in {self.refresh_seconds}s")

    def start_timer_loop(self):
        """Ticks countdown timer and drains UI updates on the main thread."""
        def tick():
            self.process_queue()
            if not self.is_refreshing:
                if self.countdown_remaining > 0:
                    self.countdown_remaining -= 1
                    self.lbl_footer.configure(text=f"Auto-refresh in {self.countdown_remaining}s")
                else:
                    self.trigger_refresh()
            self.root.after(250, tick)

        self.root.after(250, tick)

def main():
    root = tk.Tk()
    app = ClaudeTrackerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
