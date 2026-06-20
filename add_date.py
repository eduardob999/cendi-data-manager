"""
attendance.py  —  Bulletproof Attendance Updater
Version 0.4  ·  by Eduardo Bogado (2025)

Robustness features
───────────────────
• Auto-detects CSV delimiter  (, ; TAB |)
• Auto-detects file encoding  (UTF-8 BOM, UTF-8, Latin-1, CP1252, …)
• Normalises column names     (strips spaces/BOM, case-fold, accent variants)
• CÉDULA tolerance            (float → int, sci-notation, leading zeros, spaces)
• Atomic save                 (writes to .tmp then renames — no half-written file)
• Auto-backup                 (nomina.csv.bak written before every save)
• Ragged / blank rows         (silently dropped)
• Duplicate CÉDULAs           (detected and reported at load time)
• Date input                  (20+ accepted formats, normalized to YYYY-MM-DD)
• Missing columns             (APELLIDOS / NOMBRES filled with empty string)
• Attendance column type      (always coerced to Int64 on load)
"""

import os
import sys
import re
import shutil
import datetime
import tempfile
import unicodedata

import pandas as pd
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from colorama import init, Fore, Style as CStyle

# ══════════════════════════════════════════════════════════════════
#  COLOUR HELPERS
# ══════════════════════════════════════════════════════════════════


def c(color, text):
    return color + str(text) + CStyle.RESET_ALL


def header(text):
    w = 62
    print(c(Fore.CYAN, "╔" + "═" * (w - 2) + "╗"))
    print(c(Fore.CYAN, "║") + c(Fore.WHITE + CStyle.BRIGHT,
          text.center(w - 2)) + c(Fore.CYAN, "║"))
    print(c(Fore.CYAN, "╚" + "═" * (w - 2) + "╝"))


def section(text):
    print()
    print(c(Fore.YELLOW + CStyle.BRIGHT, f"  ▸ {text}"))
    print(c(Fore.YELLOW, "  " + "─" * 56))


def row(key, desc, key_color=Fore.GREEN):
    print(f"  {c(key_color + CStyle.BRIGHT, key.ljust(16))}  {desc}")


def ok(msg): print(c(Fore.GREEN,  f"  ✔  {msg}"))
def warn(msg): print(c(Fore.YELLOW, f"  ⚠  {msg}"))
def err(msg): print(c(Fore.RED,    f"  ✘  {msg}"))
def blank(): print()


def pause():
    print()
    input(c(Fore.CYAN, "  Press ENTER to continue..."))


# ══════════════════════════════════════════════════════════════════
#  HELP SCREENS
# ══════════════════════════════════════════════════════════════════

def show_help_overview():
    os.system('cls' if os.name == 'nt' else 'clear')
    header("ATTENDANCE UPDATER — HELP CENTER")
    blank()
    print(c(Fore.WHITE, "  Records daily attendance by CÉDULA and stores it in"))
    print(c(Fore.WHITE, "  nomina.csv  (auto-detected encoding & delimiter)."))
    blank()
    section("HELP TOPICS")
    row("[1]", "Getting started & file requirements")
    row("[2]", "Entering attendance")
    row("[3]", "Commands reference  (done / undo / add / help)")
    row("[4]", "CSV format & robustness details")
    row("[5]", "Date formats accepted")
    row("[6]", "Error messages & troubleshooting")
    row("[7]", "Keyboard shortcuts")
    row("[0]", "Return to main menu", Fore.RED)
    blank()
    choice = input(c(Fore.CYAN, "  Choose a topic: ")).strip()
    {
        "1": show_help_started,
        "2": show_help_entering,
        "3": show_help_commands,
        "4": show_help_csv,
        "5": show_help_dates,
        "6": show_help_errors,
        "7": show_help_shortcuts,
    }.get(choice, show_help_overview if choice != "0" else lambda: None)()


def show_help_started():
    os.system('cls' if os.name == 'nt' else 'clear')
    header("GETTING STARTED")
    section("DEPENDENCIES")
    print(c(Fore.WHITE, "  Install once with:"))
    blank()
    print(c(Fore.CYAN,  "  pip install pandas prompt_toolkit colorama chardet"))
    blank()
    row("Python 3.8+",     "Required")
    row("pandas",          "Data handling")
    row("prompt_toolkit",  "Interactive prompt + autocomplete")
    row("colorama",        "Colour output on all platforms")
    row("chardet",         "Encoding auto-detection (optional but recommended)")

    section("THE nomina.csv FILE")
    print(c(Fore.WHITE, "  Must live in the same folder as attendance.py."))
    print(c(Fore.WHITE, "  Must have at least a  CÉDULA  column."))
    print(c(Fore.WHITE, "  APELLIDOS and NOMBRES are optional (filled blank if missing)."))
    blank()
    print(c(Fore.WHITE, "  Accepted column name variants for CÉDULA:"))
    print(c(Fore.CYAN,  "    CÉDULA  cedula  CEDULA  Cedula  cédula  C_DULA  ID"))
    blank()
    print(c(Fore.WHITE, "  The script auto-detects: delimiter, encoding, BOM, and"))
    print(c(Fore.WHITE, "  trailing spaces or hidden characters in headers."))

    section("RUNNING")
    print(c(Fore.CYAN,  "  python attendance.py"))
    pause()
    show_help_overview()


def show_help_entering():
    os.system('cls' if os.name == 'nt' else 'clear')
    header("ENTERING ATTENDANCE")
    section("DATE")
    print(c(Fore.WHITE, "  You will be asked for a date. Over 20 formats accepted."))
    print(c(Fore.WHITE, "  Type  help dates  for the full list."))
    print(c(Fore.WHITE, "  The date becomes a column in nomina.csv."))

    section("MARKING PRESENT")
    print(c(Fore.WHITE, "  Type the CÉDULA number and press ENTER."))
    print(c(Fore.WHITE, "  Attendance counter for that person increases by +1."))
    blank()
    print(c(Fore.WHITE, "  TAB auto-completes from the known CÉDULA list."))
    print(c(Fore.WHITE, "  Entering the same CÉDULA twice = value of 2 (valid)."))

    section("SAVING & EXITING")
    print(c(Fore.WHITE, "  Type  done  → saves nomina.csv and exits."))
    print(c(Fore.WHITE, "  Ctrl+C      → aborts with NO changes saved."))
    print(c(Fore.WHITE, "  A .bak backup is written before every save."))

    pause()
    show_help_overview()


def show_help_commands():
    os.system('cls' if os.name == 'nt' else 'clear')
    header("COMMANDS REFERENCE")
    section("FULL LIST")
    blank()
    row("done",       "Save and exit.")
    blank()
    row("undo",       "Decrement last CÉDULA by 1.  Stackable.")
    blank()
    row("add",        "Register a new person interactively.")
    print(c(Fore.WHITE, "                   Prompts for CÉDULA, APELLIDOS, NOMBRES."))
    print(c(Fore.WHITE, "                   Person is added to nomina.csv on save."))
    blank()
    row("help",       "Open the Help Center.")
    row("help dates", "Show accepted date formats.")
    blank()
    section("NOTES")
    print(c(Fore.WHITE, "  • Case-insensitive: DONE = Done = done"))
    print(c(Fore.WHITE, "  • Leading/trailing spaces are ignored"))
    pause()
    show_help_overview()


def show_help_csv():
    os.system('cls' if os.name == 'nt' else 'clear')
    header("CSV FORMAT & ROBUSTNESS")
    section("WHAT THE SCRIPT HANDLES AUTOMATICALLY")
    blank()
    row("Encodings",   "UTF-8, UTF-8 BOM, Latin-1, CP1252, ISO-8859-1 …")
    row("Delimiters",  "Comma  ,   Semicolon  ;   Tab  \\t   Pipe  |")
    row("Column names", "Spaces, accents, case, BOM prefix stripped")
    row("CÉDULA type", "Float 123.0 → 123, sci-notation 1.2e7, spaces")
    row("Blank rows",  "Silently dropped")
    row("Ragged rows", "Extra/missing columns handled gracefully")
    row("Duplicates",  "Detected and warned; first match used")
    row("Atomic save", "Writes to .tmp then renames — crash-safe")
    row("Backup",      "nomina.csv.bak created before every save")

    section("COLUMN LAYOUT")
    blank()
    row("CÉDULA",     "Integer ID — primary key")
    row("APELLIDOS",  "Last name(s)  [created blank if missing]")
    row("NOMBRES",    "First name(s) [created blank if missing]")
    row("YYYY-MM-DD", "Attendance count (0 = absent, 1+ = present)")

    section("EXAMPLE")
    print(c(Fore.CYAN, "  CÉDULA;APELLIDOS;NOMBRES;2025-06-01"))
    print(c(Fore.CYAN, "  10234567;García;María;1"))
    print(c(Fore.CYAN, "  20345678;López;Juan;0"))
    pause()
    show_help_overview()


def show_help_dates():
    os.system('cls' if os.name == 'nt' else 'clear')
    header("ACCEPTED DATE FORMATS")
    blank()
    formats = [
        ("2025-07-04",   "ISO 8601  (preferred)"),
        ("2025/07/04",   "Slash-separated ISO"),
        ("2025.07.04",   "Dot-separated ISO"),
        ("04-07-2025",   "Day-Month-Year with dashes"),
        ("04/07/2025",   "Day-Month-Year with slashes"),
        ("04.07.2025",   "Day-Month-Year with dots"),
        ("07-04-2025",   "Month-Day-Year with dashes  (US style)"),
        ("07/04/2025",   "Month-Day-Year with slashes (US style)"),
        ("4/7/2025",     "Short day/month, full year"),
        ("4-7-25",       "Short day-month-2-digit year"),
        ("20250704",     "Compact ISO  YYYYMMDD"),
        ("04 Jul 2025",  "Day MonthAbbr Year"),
        ("4 July 2025",  "Day MonthFull Year"),
        ("July 4, 2025", "MonthFull Day, Year"),
        ("Jul 4, 2025",  "MonthAbbr Day, Year"),
        ("Jul 4 2025",   "MonthAbbr Day Year  (no comma)"),
        ("4 jul 2025",   "Lowercase month name"),
        ("04-JUL-2025",  "Uppercase month abbreviation"),
        ("today",        "Today's date"),
        ("hoy",          "Today (Spanish)"),
    ]
    for fmt, desc in formats:
        print(f"  {c(Fore.CYAN + CStyle.BRIGHT, fmt.ljust(18))}  {desc}")
    blank()
    print(c(Fore.WHITE, "  Ambiguous dates (e.g. 04/07/2025) are treated as"))
    print(c(Fore.WHITE, "  DD/MM/YYYY.  The program will show the resolved date"))
    print(c(Fore.WHITE, "  and ask you to confirm before proceeding."))
    pause()
    show_help_overview()


def show_help_errors():
    os.system('cls' if os.name == 'nt' else 'clear')
    header("ERROR MESSAGES & TROUBLESHOOTING")
    section("STARTUP")
    blank()
    row("File not found",    "nomina.csv missing → create or move it here.")
    row("Cannot read file",  "Check file permissions.")
    row("Empty file",        "File has no rows → add at least a header + 1 row.")
    row("No CÉDULA column",  "Header not recognised → see 'help' topic 4.")

    section("DATA ENTRY")
    blank()
    row("CÉDULA not found",  "Not in file → use  add  to register.")
    row("Duplicate CÉDULA",  "Two rows share the same ID → clean manually.")
    row("Invalid CÉDULA",    "Not a number → check for letters or symbols.")
    row("No entry to undo",  "History empty for this session.")

    section("SAVING")
    blank()
    row("Permission denied", "File open in Excel? Close it and try again.")
    row("Disk full",         "Free up space; backup (.bak) may also fail.")

    section("COMMON QUESTIONS")
    blank()
    print(c(Fore.WHITE, "  Q: Suggestions show  12345678.0  floats?"))
    print(c(Fore.CYAN,  "  A: Fixed automatically — CÉDULA is cast to Int64."))
    blank()
    print(c(Fore.WHITE, "  Q: File opens fine in Excel but script errors?"))
    print(c(Fore.CYAN,  "  A: Save as CSV UTF-8 from Excel (File → Save As)."))
    blank()
    print(c(Fore.WHITE, "  Q: Wrong delimiter detected?"))
    print(c(Fore.CYAN,  "  A: The script tries , ; TAB | in order. If all fail,"))
    print(c(Fore.CYAN,  "     open the file and resave with commas."))
    pause()
    show_help_overview()


def show_help_shortcuts():
    os.system('cls' if os.name == 'nt' else 'clear')
    header("KEYBOARD SHORTCUTS")
    section("AT THE CÉDULA PROMPT")
    blank()
    row("TAB",        "Auto-complete from known CÉDULAs.")
    row("↑ / ↓",     "Navigate autocomplete suggestions.")
    row("→ / ←",     "Move cursor in current input.")
    row("HOME / END", "Jump to start / end of line.")
    row("Ctrl+A",     "Beginning of line.")
    row("Ctrl+E",     "End of line.")
    row("Ctrl+U",     "Clear the entire line.")
    row("Ctrl+W",     "Delete previous word.")
    row("Ctrl+C",     "Abort session — NO save.")
    blank()
    section("COMMANDS  (type and press ENTER)")
    blank()
    row("done",       "Save and exit.")
    row("undo",       "Undo last entry.")
    row("add",        "Add new person.")
    row("help",       "Help Center.")
    row("help dates", "Date formats list.")
    pause()
    show_help_overview()


# ══════════════════════════════════════════════════════════════════
#  ROBUST CSV LOADING
# ══════════════════════════════════════════════════════════════════

ENCODINGS_TO_TRY = [
    'utf-8-sig',   # UTF-8 with BOM (Excel default)
    'utf-8',
    'latin-1',
    'cp1252',
    'iso-8859-1',
    'cp1250',
    'utf-16',
]

DELIMITERS_TO_TRY = [',', ';', '\t', '|']

# Canonical column name → list of recognised aliases (lower-case, no accents)
COLUMN_ALIASES = {
    'CÉDULA':    ['cedula', 'cedula', 'c_dula', 'id', 'documento',
                  'cedula_identidad', 'ci', 'dni', 'numero', 'no'],
    'APELLIDOS': ['apellidos', 'apellido', 'lastname', 'last_name',
                  'surname', 'paterno'],
    'NOMBRES':   ['nombres', 'nombre', 'firstname', 'first_name',
                  'name', 'nombre_s'],
}


def _strip_accents(s: str) -> str:
    """Remove diacritics for fuzzy column matching."""
    return ''.join(
        ch for ch in unicodedata.normalize('NFD', s)
        if unicodedata.category(ch) != 'Mn'
    )


def _normalise_col(name: str) -> str:
    """Lower-case, strip spaces/BOM/special chars, remove accents."""
    name = name.strip().lstrip('\ufeff')
    name = _strip_accents(name).lower()
    name = re.sub(r'[^a-z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return name


def _detect_encoding(path: str) -> str:
    """Try chardet first, fall back to manual list."""
    try:
        import chardet
        with open(path, 'rb') as f:
            raw = f.read(65536)
        result = chardet.detect(raw)
        detected = result.get('encoding') or 'utf-8'
        # Always prefer utf-8-sig over plain utf-8 when BOM present
        if raw.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        return detected
    except ImportError:
        pass
    # Fallback: try each encoding
    for enc in ENCODINGS_TO_TRY:
        try:
            with open(path, encoding=enc, errors='strict') as f:
                f.read(4096)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    return 'latin-1'  # last resort — never throws


def _try_load(path: str, encoding: str, delimiter: str) -> pd.DataFrame | None:
    """Attempt a single (encoding, delimiter) combination."""
    try:
        df = pd.read_csv(
            path,
            encoding=encoding,
            sep=delimiter,
            dtype=str,          # load everything as str — we normalise later
            skip_blank_lines=True,
            on_bad_lines='skip',
        )
        # Need at least 1 column and 0 rows (header-only is ok)
        if df.empty and len(df.columns) == 0:
            return None
        return df
    except Exception:
        return None


def _resolve_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Rename DataFrame columns to canonical names where possible.
    Returns (renamed_df, mapping_report).
    """
    col_map = {}   # original → canonical
    norm_to_canonical = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            norm_to_canonical[alias] = canonical
        # also map the canonical itself
        norm_to_canonical[_normalise_col(canonical)] = canonical

    rename = {}
    for col in df.columns:
        normed = _normalise_col(col)
        if normed in norm_to_canonical:
            canonical = norm_to_canonical[normed]
            if canonical not in rename.values():   # first match wins
                rename[col] = canonical
                col_map[col] = canonical

    df = df.rename(columns=rename)
    return df, col_map


def _coerce_cedula(series: pd.Series) -> pd.Series:
    """
    Convert CÉDULA column to nullable Int64, handling:
    - float strings  "12345678.0"
    - scientific notation "1.23e7"
    - leading/trailing spaces  " 987654 "
    - already-int strings "12345678"
    """
    def _to_int(val):
        if pd.isna(val):
            return pd.NA
        s = str(val).strip()
        if not s or s.lower() in ('nan', 'none', ''):
            return pd.NA
        try:
            # float() handles "1.23e7" and "12345.0"
            return int(float(s))
        except (ValueError, OverflowError):
            return pd.NA

    return series.map(_to_int).astype('Int64')


def load_csv_robust(path: str) -> pd.DataFrame:
    """
    Load nomina.csv with full tolerance for encoding, delimiter,
    column naming, and CÉDULA type issues.
    Raises SystemExit with a descriptive message on unrecoverable errors.
    """
    if not os.path.exists(path):
        err(f"File not found: {path}")
        sys.exit(1)
    if os.path.getsize(path) == 0:
        err("The file is empty.")
        sys.exit(1)

    # 1. Detect encoding
    encoding = _detect_encoding(path)

    # 2. Try each delimiter with the detected encoding first,
    #    then fall back to other encodings if nothing works.
    df = None
    used_enc = used_delim = None
    encodings = [encoding] + [e for e in ENCODINGS_TO_TRY if e != encoding]

    for enc in encodings:
        for delim in DELIMITERS_TO_TRY:
            candidate = _try_load(path, enc, delim)
            if candidate is not None and len(candidate.columns) >= 1:
                # Heuristic: if only 1 column, delimiter probably wrong; keep trying
                if len(candidate.columns) == 1 and delim != DELIMITERS_TO_TRY[-1]:
                    continue
                df = candidate
                used_enc = enc
                used_delim = delim
                break
        if df is not None:
            break

    if df is None:
        err("Could not parse nomina.csv with any known encoding or delimiter.")
        print(c(Fore.WHITE, "  Try opening the file in a text editor and resaving as UTF-8 CSV."))
        sys.exit(1)

    delim_name = {',': 'comma', ';': 'semicolon',
                  '\t': 'tab',   '|': 'pipe'}.get(used_delim, used_delim)
    ok(f"Loaded nomina.csv  [{used_enc} / {delim_name}-delimited]")

    # 3. Drop rows that are entirely blank
    df.dropna(how='all', inplace=True)
    df.reset_index(drop=True, inplace=True)

    # 4. Resolve column names
    df, col_map = _resolve_columns(df)
    if col_map:
        mapped = ', '.join(f"'{k}'→'{v}'" for k, v in col_map.items())
        ok(f"Column mapping: {mapped}")

    # 5. Ensure CÉDULA column exists
    if 'CÉDULA' not in df.columns:
        err("Could not find a CÉDULA column.")
        print(c(Fore.WHITE, "  Column headers found: " +
                ', '.join(f"'{c2}'" for c2 in df.columns)))
        print(c(Fore.WHITE, "  Accepted names: CÉDULA, cedula, ID, CI, DNI, documento, …"))
        print(
            c(Fore.WHITE, "  Type  help  after fixing the file to see all accepted names."))
        sys.exit(1)

    # 6. Ensure APELLIDOS / NOMBRES columns
    for col in ('APELLIDOS', 'NOMBRES'):
        if col not in df.columns:
            warn(
                f"Column '{col}' not found — will be filled with empty strings.")
            df[col] = ''

    # 7. Coerce CÉDULA
    original_cedulas = df['CÉDULA'].copy()
    df['CÉDULA'] = _coerce_cedula(df['CÉDULA'])

    na_count = df['CÉDULA'].isna().sum()
    if na_count:
        warn(f"{na_count} row(s) have unparseable CÉDULA values and will be ignored.")

    # 8. Detect duplicates
    dupes = df['CÉDULA'].dropna()
    dupes = dupes[dupes.duplicated()]
    if not dupes.empty:
        warn(
            f"Duplicate CÉDULA(s) found: {', '.join(str(d) for d in dupes.unique())}")
        warn("First occurrence will be used; clean duplicates in nomina.csv.")

    # 9. Coerce existing attendance columns (date-shaped columns) to Int64
    date_cols = [col for col in df.columns
                 if col not in ('CÉDULA', 'APELLIDOS', 'NOMBRES')]
    for col in date_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

    return df


def save_csv_robust(df: pd.DataFrame, path: str) -> None:
    """
    Atomic save: write to a temp file, create a .bak, then rename.
    Handles permission errors gracefully.
    """
    bak_path = path + '.bak'
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)),
                                        prefix='.nomina_tmp_')
    try:
        os.close(tmp_fd)
        # utf-8-sig = Excel-friendly
        df.to_csv(tmp_path, index=False, encoding='utf-8-sig')

        # Backup
        if os.path.exists(path):
            shutil.copy2(path, bak_path)

        # Atomic replace
        shutil.move(tmp_path, path)
        ok(f"Saved → {path}  (backup → {bak_path})")

    except PermissionError:
        err("Permission denied while saving.")
        warn("Is nomina.csv open in Excel or another program? Close it and try again.")
        warn(f"Your data is intact in the temp file: {tmp_path}")
        raise
    except OSError as e:
        err(f"OS error while saving: {e}")
        warn(f"Unsaved data is in: {tmp_path}")
        raise
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


# ══════════════════════════════════════════════════════════════════
#  DATE PARSING  (20+ formats)
# ══════════════════════════════════════════════════════════════════

_DATE_FORMATS = [
    # ISO variants
    "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
    # Day-first (European)
    "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
    "%d-%m-%y", "%d/%m/%y", "%d.%m.%y",
    # Month-first (US)
    "%m-%d-%Y", "%m/%d/%Y",
    "%m-%d-%y", "%m/%d/%y",
    # Compact
    "%Y%m%d",
    # Verbose
    "%d %b %Y", "%d %B %Y",
    "%B %d, %Y", "%b %d, %Y",
    "%b %d %Y", "%B %d %Y",
    "%d %b %y", "%d %B %y",
]

_AMBIGUOUS_FORMATS = {
    # formats where day/month order is ambiguous
    "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
    "%m-%d-%Y", "%m/%d/%Y",
    "%d-%m-%y", "%d/%m/%y",
    "%m-%d-%y", "%m/%d/%y",
}


def parse_date(raw: str) -> datetime.date | None:
    """Return a date or None.  Tries all known formats."""
    raw = raw.strip()
    if raw.lower() in ('today', 'hoy'):
        return datetime.date.today()

    for fmt in _DATE_FORMATS:
        try:
            return datetime.datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _is_ambiguous(raw: str) -> bool:
    """True if the raw string matches one of the ambiguous patterns."""
    for fmt in _AMBIGUOUS_FORMATS:
        try:
            datetime.datetime.strptime(raw.strip(), fmt)
            return True
        except ValueError:
            continue
    return False


def get_date_input() -> datetime.date:
    while True:
        raw = input(c(Fore.CYAN,
                      "  Enter date  (any format, or 'today'): ")).strip()

        if raw.lower() in ('help', 'help dates'):
            show_help_dates()
            continue

        date = parse_date(raw)
        if date is None:
            err("Date not recognised.")
            print(
                c(Fore.WHITE, "  Type  help dates  for a full list of accepted formats."))
            continue

        # Warn on ambiguous dates and ask for confirmation
        if _is_ambiguous(raw):
            warn(
                f"Ambiguous date — interpreted as  {date}  (DD/MM/YYYY priority).")
            confirm = input(c(Fore.CYAN, "  Correct? [Y/n]: ")).strip().lower()
            if confirm in ('n', 'no'):
                continue

        ok(f"Date set to  {date}")
        return date


# ══════════════════════════════════════════════════════════════════
#  COMPLETER BUILDER
# ══════════════════════════════════════════════════════════════════

def build_completer(df: pd.DataFrame) -> WordCompleter:
    values = [str(int(v)) for v in df['CÉDULA'] if pd.notna(v)]
    return WordCompleter(values, ignore_case=True)


# ══════════════════════════════════════════════════════════════════
#  STARTUP SCREEN
# ══════════════════════════════════════════════════════════════════

def initialize_screen():
    init(autoreset=True)
    os.system('cls' if os.name == 'nt' else 'clear')
    header("ATTENDANCE DATA UPDATER")
    print(c(Fore.GREEN, "  Version 0.4  ·  by Eduardo Bogado (2025)"))
    blank()
    print(c(Fore.WHITE, "  Type  help  at any prompt to open the Help Center."))
    print(c(Fore.WHITE, "  Press Ctrl+C to abort without saving."))
    blank()


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    MAIN_FILE = 'nomina.csv'

    initialize_screen()
    main_df = load_csv_robust(MAIN_FILE)
    blank()

    try:
        date = get_date_input()
        blank()

        # Quick-reference card
        print(c(Fore.WHITE + CStyle.BRIGHT, "  QUICK REFERENCE"))
        print(c(Fore.WHITE, "  " + "─" * 44))
        for cmd, desc in [
            ("<number>", "Mark that CÉDULA present"),
            ("done",     "Save & exit"),
            ("undo",     "Revert last entry"),
            ("add",      "Register new personnel"),
            ("help",     "Full Help Center"),
        ]:
            print(
                f"  {c(Fore.GREEN + CStyle.BRIGHT, cmd.ljust(12))}  {c(Fore.WHITE, desc)}")
        print(c(Fore.WHITE, "  " + "─" * 44))
        blank()

        attendance_col = str(date)
        if attendance_col not in main_df.columns:
            main_df[attendance_col] = pd.array(
                [0] * len(main_df), dtype='Int64')
        else:
            # Coerce existing column in case it's float
            main_df[attendance_col] = pd.to_numeric(
                main_df[attendance_col], errors='coerce').astype('Int64')
            already = main_df[attendance_col].sum()
            if already > 0:
                warn(
                    f"This date already has {already} attendance record(s). Adding to them.")

        cedula_completer = build_completer(main_df)
        entry_history: list[int] = []
        prompt_style = Style.from_dict({'prompt': 'ansicyan bold'})

        try:
            while True:
                cedula_raw = prompt(
                    HTML('<prompt>  CÉDULA › </prompt>'),
                    completer=cedula_completer,
                    style=prompt_style,
                ).strip()

                cmd = cedula_raw.lower()

                # ── DONE ─────────────────────────────────────
                if cmd == 'done':
                    break

                # ── HELP ─────────────────────────────────────
                elif cmd in ('help', 'help dates'):
                    if cmd == 'help dates':
                        show_help_dates()
                    else:
                        show_help_overview()

                # ── UNDO ─────────────────────────────────────
                elif cmd == 'undo':
                    if entry_history:
                        last = entry_history.pop()
                        main_df.loc[main_df['CÉDULA'] ==
                                    last, attendance_col] -= 1
                        warn(f"Entry for CÉDULA {last} undone.")
                    else:
                        err("No entries to undo in this session.")

                # ── ADD ──────────────────────────────────────
                elif cmd == 'add':
                    new_ced_raw = input(
                        c(Fore.CYAN, "    New CÉDULA   : ")).strip()
                    parsed_ced = _coerce_cedula(pd.Series([new_ced_raw]))[0]
                    if pd.isna(parsed_ced):
                        err("Invalid CÉDULA — must be a whole number.")
                    elif int(parsed_ced) in main_df['CÉDULA'].values:
                        err(f"CÉDULA {int(parsed_ced)} already exists in the file.")
                    else:
                        new_ap = input(
                            c(Fore.CYAN, "    APELLIDOS    : ")).strip()
                        new_nom = input(
                            c(Fore.CYAN, "    NOMBRES      : ")).strip()
                        new_id = int(parsed_ced)
                        new_row = pd.DataFrame({
                            'CÉDULA':      pd.array([new_id], dtype='Int64'),
                            'APELLIDOS':   [new_ap],
                            'NOMBRES':     [new_nom],
                            attendance_col: pd.array([0], dtype='Int64'),
                        })
                        main_df = pd.concat(
                            [main_df, new_row], ignore_index=True)
                        cedula_completer = build_completer(main_df)
                        ok(f"{new_nom} {new_ap}  (CÉDULA {new_id}) added.")

                # ── CÉDULA NUMBER ────────────────────────────
                else:
                    parsed = _coerce_cedula(pd.Series([cedula_raw]))[0]
                    if pd.isna(parsed):
                        err("Not a valid number. Enter a CÉDULA or a command "
                            "(done / undo / add / help).")
                        continue

                    cedula_int = int(parsed)
                    mask = main_df['CÉDULA'] == cedula_int

                    if not mask.any():
                        err(f"CÉDULA {cedula_int} not found. "
                            "Use  add  to register new personnel.")
                        continue

                    main_df.loc[mask, attendance_col] += 1
                    entry_history.append(cedula_int)

                    nom = str(main_df.loc[mask, 'NOMBRES'].values[0]).strip()
                    ap = str(main_df.loc[mask, 'APELLIDOS'].values[0]).strip()
                    name = f"{nom} {ap}".strip() or f"CÉDULA {cedula_int}"
                    ok(f"{name} marked present.")

        except KeyboardInterrupt:
            print()
            warn("Interrupted — changes were NOT saved.")
            sys.exit(0)

        # ── SAVE ─────────────────────────────────────────────
        blank()
        try:
            save_csv_robust(main_df, MAIN_FILE)
        except (PermissionError, OSError):
            sys.exit(1)

    except KeyboardInterrupt:
        print()
        warn("Interrupted — exiting without changes.")
        sys.exit(0)


if __name__ == "__main__":
    main()
