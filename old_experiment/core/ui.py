"""
Terminal UI & Styling Module using Colorama.
============================================

Provides colorful, clear, and easy-to-read console formatting across all
scripts (run.py, backtest.py, regime_split.py, diagnostic.py, and sync tools).

Features:
- Windows console ANSI escape sequence initialization.
- Encoding protection for Windows consoles (cp1252 safe).
- Semantic color constants (Success, Warning, Danger, Info, Muted, Accent).
- Formatted status badges ([OK], [ERROR], [MATCH], [SKIPPED], [BULLISH], etc.).
- Modern styled banners, section headers, and dividers.
- High-visibility DataFrame and table formatter with automatic financial metrics colorization.
"""

import sys
import pandas as pd
import colorama
from colorama import Fore, Back, Style

# Safe UTF-8 reconfiguration for Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Initialize colorama with autoreset so styles never bleed into subsequent lines
colorama.init(autoreset=True)

# Enable native Windows Virtual Terminal sequences if supported (Windows 10/11)
try:
    colorama.just_fix_windows_console()
except (AttributeError, Exception):
    pass

# ------------------------------------------------------------------------------
# Semantic Color Palettes
# ------------------------------------------------------------------------------
C_RESET = Style.RESET_ALL
C_BOLD = Style.BRIGHT
C_DIM = Style.DIM

# Brand / Primary
C_PRIMARY = Fore.LIGHTCYAN_EX + Style.BRIGHT
C_SECONDARY = Fore.CYAN
C_ACCENT = Fore.LIGHTMAGENTA_EX + Style.BRIGHT
C_BORDER = Fore.LIGHTBLUE_EX
C_DIVIDER = Fore.LIGHTBLACK_EX

# Status / Feedback
C_SUCCESS = Fore.LIGHTGREEN_EX + Style.BRIGHT
C_WIN = Fore.LIGHTGREEN_EX
C_WARN = Fore.LIGHTYELLOW_EX + Style.BRIGHT
C_DANGER = Fore.LIGHTRED_EX + Style.BRIGHT
C_LOSS = Fore.LIGHTRED_EX
C_INFO = Fore.LIGHTCYAN_EX
C_MUTED = Fore.LIGHTBLACK_EX
C_VALUE = Fore.WHITE + Style.BRIGHT
C_LABEL = Fore.CYAN


# ------------------------------------------------------------------------------
# String Coloring Helpers
# ------------------------------------------------------------------------------
def green(text):
    return f"{Fore.GREEN}{text}{C_RESET}"


def bright_green(text):
    return f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}{text}{C_RESET}"


def red(text):
    return f"{Fore.RED}{text}{C_RESET}"


def bright_red(text):
    return f"{Fore.LIGHTRED_EX}{Style.BRIGHT}{text}{C_RESET}"


def yellow(text):
    return f"{Fore.YELLOW}{text}{C_RESET}"


def bright_yellow(text):
    return f"{Fore.LIGHTYELLOW_EX}{Style.BRIGHT}{text}{C_RESET}"


def cyan(text):
    return f"{Fore.CYAN}{text}{C_RESET}"


def bright_cyan(text):
    return f"{Fore.LIGHTCYAN_EX}{Style.BRIGHT}{text}{C_RESET}"


def blue(text):
    return f"{Fore.BLUE}{text}{C_RESET}"


def bright_blue(text):
    return f"{Fore.LIGHTBLUE_EX}{Style.BRIGHT}{text}{C_RESET}"


def magenta(text):
    return f"{Fore.MAGENTA}{text}{C_RESET}"


def bright_magenta(text):
    return f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}{text}{C_RESET}"


def white(text):
    return f"{Fore.WHITE}{text}{C_RESET}"


def bright_white(text):
    return f"{Fore.LIGHTWHITE_EX}{Style.BRIGHT}{text}{C_RESET}"


def dim(text):
    return f"{Style.DIM}{text}{C_RESET}"


def bold(text):
    return f"{Style.BRIGHT}{text}{C_RESET}"


# ------------------------------------------------------------------------------
# Badges & Status Indicators (ASCII safe for all Windows consoles)
# ------------------------------------------------------------------------------
def badge(text, color=Fore.CYAN, bracket_color=Fore.LIGHTBLACK_EX):
    return f"{bracket_color}[{color}{text}{bracket_color}]{C_RESET}"


def badge_success(text="SUCCESS"):
    return f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}[OK: {text}]{C_RESET}"


def badge_error(text="ERROR"):
    return f"{Fore.LIGHTRED_EX}{Style.BRIGHT}[! {text}]{C_RESET}"


def badge_warn(text="WARNING"):
    return f"{Fore.LIGHTYELLOW_EX}{Style.BRIGHT}[! {text}]{C_RESET}"


def badge_info(text="INFO"):
    return f"{Fore.LIGHTCYAN_EX}{Style.BRIGHT}[i {text}]{C_RESET}"


def badge_match(text="MATCH"):
    return f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT} {text} {C_RESET}"


def badge_skip(text="SKIPPED"):
    return f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT} {text} {C_RESET}"


def badge_drive(text="Google Drive"):
    return f"{Fore.LIGHTBLUE_EX}{Style.BRIGHT}[{text}]{C_RESET}"


def badge_sheets(text="Google Sheets"):
    return f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}[{text}]{C_RESET}"


def badge_regime(regime_name):
    r_str = str(regime_name).strip().capitalize()
    if r_str == "Bullish":
        return f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT} BULLISH {C_RESET}"
    elif r_str == "Bearish":
        return f"{Back.RED}{Fore.WHITE}{Style.BRIGHT} BEARISH {C_RESET}"
    elif r_str == "Neutral":
        return f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT} NEUTRAL {C_RESET}"
    return f"{Back.BLUE}{Fore.WHITE}{Style.BRIGHT} {r_str.upper()} {C_RESET}"


# ------------------------------------------------------------------------------
# Dividers, Headers, and Framing
# ------------------------------------------------------------------------------
def divider(width=70, char="-", color=C_DIVIDER):
    return f"{color}{char * width}{C_RESET}"


def header(title, width=70, char="=", color=C_BORDER):
    line = f"{color}{char * width}{C_RESET}"
    text = f"{C_PRIMARY}{title}{C_RESET}"
    return f"\n{line}\n  {text}\n{line}"


def sub_header(title, width=70, char="-", color=Fore.CYAN):
    line = f"{color}{char * width}{C_RESET}"
    text = f"{Fore.LIGHTYELLOW_EX}{Style.BRIGHT}{title}{C_RESET}"
    return f"\n{line}\n  {text}\n{line}"


def banner_box(title, subtitle=None, width=70, color=C_BORDER, char="="):
    top_bot = f"{color}{char * width}{C_RESET}"
    title_line = f"  {C_PRIMARY}{title}{C_RESET}"
    lines = [f"\n{top_bot}", title_line]
    if subtitle:
        if isinstance(subtitle, list):
            for sub in subtitle:
                lines.append(f"  {Fore.WHITE}{sub}{C_RESET}")
        else:
            lines.append(f"  {Fore.WHITE}{subtitle}{C_RESET}")
    lines.append(top_bot)
    return "\n".join(lines)


# ------------------------------------------------------------------------------
# Key-Value and Metrics Formatting
# ------------------------------------------------------------------------------
def key_val(key, val, key_width=26, key_color=C_LABEL, val_color=None):
    if val_color is None:
        val_color = C_VALUE
    return f"  {key_color}{key:<{key_width}}{C_RESET} {val_color}{val}{C_RESET}"


def format_pct(val, positive_is_good=True, decimals=1, include_sign=True):
    try:
        num = float(val)
    except (ValueError, TypeError):
        return str(val)

    sign = "+" if include_sign and num > 0 else ""
    formatted = f"{sign}{num:.{decimals}f}%"

    if num > 0:
        return f"{Fore.LIGHTGREEN_EX if positive_is_good else Fore.LIGHTRED_EX}{formatted}{C_RESET}"
    elif num < 0:
        return f"{Fore.LIGHTRED_EX if positive_is_good else Fore.LIGHTGREEN_EX}{formatted}{C_RESET}"
    else:
        return f"{Fore.LIGHTBLACK_EX}{formatted}{C_RESET}"


def format_currency(val, prefix="Rs "):
    try:
        num = float(val)
        formatted = f"{prefix}{num:,.2f}"
        return f"{Fore.WHITE}{Style.BRIGHT}{formatted}{C_RESET}"
    except (ValueError, TypeError):
        return str(val)


# ------------------------------------------------------------------------------
# High-Visibility Terminal DataFrame Table Formatter
# ------------------------------------------------------------------------------
def render_table(df, title=None, width=None, max_rows=None):
    """
    Renders a pandas DataFrame into a beautifully aligned, colorful console table.
    - Headers in bold Cyan.
    - Separator bar.
    - Auto-formats financial columns (WinRate%, ProfitFactor, ReturnPct, Drawdown, etc.).
    - Preserves exact column alignment without ANSI code distortion.
    """
    if df is None or df.empty:
        return f"{Fore.LIGHTYELLOW_EX}(Empty dataset){C_RESET}"

    display_df = df.head(max_rows) if max_rows and len(df) > max_rows else df
    cols = list(display_df.columns)

    # 1. Determine raw string length for each column to guarantee perfect column alignment
    raw_lengths = {}
    for c in cols:
        lengths = [len(str(c))]
        for val in display_df[c]:
            lengths.append(len(str(val) if not pd.isna(val) else "-"))
        raw_lengths[c] = max(lengths)

    # 2. Build Header
    hdr_cells = []
    sep_cells = []
    for c in cols:
        w = raw_lengths[c]
        hdr_cells.append(f"{Fore.LIGHTCYAN_EX}{Style.BRIGHT}{c:<{w}}{C_RESET}")
        sep_cells.append(f"{Fore.LIGHTBLACK_EX}{'-' * w}{C_RESET}")

    hdr_line = "  " + "   ".join(hdr_cells)
    sep_line = "  " + "   ".join(sep_cells)

    lines = []
    if title:
        lines.append(f"\n{Fore.LIGHTYELLOW_EX}{Style.BRIGHT}{title}{C_RESET}")
    lines.append(hdr_line)
    lines.append(sep_line)

    # 3. Format Data Rows
    for _, row in display_df.iterrows():
        row_cells = []
        for c in cols:
            val = row[c]
            raw_str = "-" if pd.isna(val) else str(val)
            w = raw_lengths[c]

            is_num = isinstance(val, (int, float)) and not pd.isna(val)
            padded = raw_str.rjust(w) if is_num else raw_str.ljust(w)

            # Context-sensitive color assignment
            cell_color = Fore.WHITE
            col_lower = c.lower()

            if is_num:
                num_val = float(val)
                if any(k in col_lower for k in ("winrate", "win rate")):
                    if num_val >= 50.0:
                        cell_color = Fore.LIGHTGREEN_EX + Style.BRIGHT
                    elif num_val >= 40.0:
                        cell_color = Fore.LIGHTYELLOW_EX
                    else:
                        cell_color = Fore.LIGHTRED_EX
                elif any(k in col_lower for k in ("profitfactor", "profit_factor")):
                    if num_val >= 1.5:
                        cell_color = Fore.LIGHTGREEN_EX + Style.BRIGHT
                    elif num_val >= 1.0:
                        cell_color = Fore.LIGHTYELLOW_EX
                    else:
                        cell_color = Fore.LIGHTRED_EX
                elif any(k in col_lower for k in ("drawdown",)):
                    cell_color = Fore.LIGHTRED_EX
                elif any(k in col_lower for k in ("return", "expectancy", "rupeepnl", "pnl")):
                    if num_val > 0:
                        cell_color = Fore.LIGHTGREEN_EX
                    elif num_val < 0:
                        cell_color = Fore.LIGHTRED_EX
                    else:
                        cell_color = Fore.LIGHTBLACK_EX
                elif "trades" in col_lower or "count" in col_lower:
                    cell_color = Fore.LIGHTCYAN_EX
                elif "stop" in col_lower:
                    cell_color = Fore.LIGHTRED_EX
                elif "target" in col_lower:
                    cell_color = Fore.LIGHTGREEN_EX
                elif "entry" in col_lower:
                    cell_color = Fore.LIGHTWHITE_EX
            else:
                str_val = raw_str.strip()
                if col_lower == "regime":
                    if str_val.lower() == "bullish":
                        cell_color = Fore.LIGHTGREEN_EX + Style.BRIGHT
                    elif str_val.lower() == "bearish":
                        cell_color = Fore.LIGHTRED_EX + Style.BRIGHT
                    elif str_val.lower() == "neutral":
                        cell_color = Fore.LIGHTYELLOW_EX + Style.BRIGHT
                elif col_lower in ("stock", "ticker"):
                    cell_color = Fore.LIGHTWHITE_EX + Style.BRIGHT
                elif col_lower == "strategy":
                    cell_color = Fore.LIGHTYELLOW_EX
                elif col_lower == "exitreason":
                    if "target" in str_val:
                        cell_color = Fore.LIGHTGREEN_EX
                    elif "stop" in str_val:
                        cell_color = Fore.LIGHTRED_EX
                    elif "time" in str_val:
                        cell_color = Fore.LIGHTYELLOW_EX

            row_cells.append(f"{cell_color}{padded}{C_RESET}")

        lines.append("  " + "   ".join(row_cells))

    if max_rows and len(df) > max_rows:
        lines.append(f"  {Fore.LIGHTBLACK_EX}... and {len(df) - max_rows} more row(s) ...{C_RESET}")

    return "\n".join(lines)
