# COVID Time Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a BeeWare (Toga + Briefcase) desktop app that displays "COVID time" — the real weekday/time/timezone with the date frozen at March 2020 and a climbing day counter — and verify it packages locally for macOS.

**Architecture:** The time math (refactored from [jepler's `covidtime.py`](https://codeberg.org/jepler/junkdrawer/src/branch/main/d0a6j6ey/covidtime.py)) lives in a pure, injectable `clock.py` module with no GUI dependencies, fully unit-tested. `app.py` is a thin Toga shell: a fixed-size window with a day counter + COVID-time line, refreshed each second by an `async def on_running()` coroutine on Toga's event loop. Briefcase scaffolds and packages the project.

**Tech Stack:** Python 3.14, Toga 0.5.x (GUI), Briefcase 0.3.x (packaging), pytest (tests).

**Design spec:** [`docs/superpowers/specs/2026-06-14-covid-time-design.md`](../specs/2026-06-14-covid-time-design.md)

---

## File Structure

| Path | Responsibility | Created in |
|---|---|---|
| `.gitignore` | Ignore venv, build artifacts, `__pycache__` | Task 1 |
| `.venv/` | Project virtualenv (gitignored) | Task 1 |
| `pyproject.toml` | Briefcase config: app "COVID Time", bundle `com.kattni`, requires toga | Task 2 (scaffold) |
| `conftest.py` | Adds `src/` to `sys.path` so pytest imports `covid_time` | Task 2 |
| `src/covid_time/__init__.py`, `__main__.py` | Package marker + `main().main_loop()` entry | Task 2 (scaffold) |
| `src/covid_time/clock.py` | Pure functions `day_number()`, `covid_time_string()` | Task 3–4 |
| `src/covid_time/app.py` | Toga `App` subclass, window, `on_running` tick | Task 5 |
| `tests/test_clock.py` | Unit tests for the clock math | Task 3–4 |
| `LICENSE`, `CHANGELOG`, `README.*` | Project metadata (from scaffold) | Task 2 |

**Scope note:** This plan covers the spec's **MVP** (runnable app + local macOS package). The cross-platform **GitHub Actions matrix** (Windows/Linux binaries) is explicitly deferred to a separate future plan, per the design's "Out of scope" list.

---

## Task 1: Create the virtualenv and install the BeeWare toolchain

**Files:**
- Create: `.gitignore`
- Create: `.venv/` (gitignored, not committed)

- [ ] **Step 1: Create the virtualenv**

Run from `/Users/kattni/BeeWare/covid_time`:
```bash
python3 -m venv .venv
```
Expected: a `.venv/` directory appears.

- [ ] **Step 2: Install Briefcase and pytest into it**

```bash
.venv/bin/pip install --upgrade pip
.venv/bin/pip install briefcase pytest
```
Expected: both install with no errors.

- [ ] **Step 3: Verify Briefcase is callable**

```bash
.venv/bin/briefcase --version
```
Expected: prints a version like `0.3.x`.

- [ ] **Step 4: Create `.gitignore`**

Create `/Users/kattni/BeeWare/covid_time/.gitignore` with:
```
# Python
__pycache__/
*.py[cod]
*.egg-info/

# Virtualenv
.venv/

# Briefcase / packaging outputs
build/
dist/
macOS/
linux/
windows/
local/
*.log
```

- [ ] **Step 5: Commit**

```bash
git add .gitignore
git commit -m "chore: add .gitignore and BeeWare toolchain setup

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Scaffold the Briefcase project into the existing repo

The repo already contains `docs/` and `.git`, so we generate the scaffold into a throwaway directory and copy only the project files in (preserving `.gitignore`, `docs/`, `.git`).

**Files:**
- Create: `pyproject.toml`, `src/covid_time/...`, `tests/`, `LICENSE`, `CHANGELOG`, `README.*` (via scaffold)
- Create: `conftest.py`
- Delete: generated sample test(s) under `tests/`

- [ ] **Step 1: Generate the scaffold into a temp directory**

```bash
SCAFFOLD_DIR="$(mktemp -d)/scaffold"
mkdir -p "$SCAFFOLD_DIR"
( cd "$SCAFFOLD_DIR" && /Users/kattni/BeeWare/covid_time/.venv/bin/briefcase new \
  --no-input \
  -Q "formal_name=COVID Time" \
  -Q "app_name=covid_time" \
  -Q "bundle=com.kattni" \
  -Q "description=A clock stuck in March 2020." \
  -Q "author=Kattni" \
  -Q "email=kattni@users.noreply.github.com" \
  -Q "url=https://github.com/kattni/covid_time" \
  -Q "license=MIT" )
```
Expected: no prompts; a `$SCAFFOLD_DIR/covid_time/` directory is created.

- [ ] **Step 2: Copy the generated project files into the repo**

```bash
SRC="$SCAFFOLD_DIR/covid_time"
DEST=/Users/kattni/BeeWare/covid_time
cp "$SRC/pyproject.toml" "$DEST/"
cp -R "$SRC/src" "$DEST/"
cp -R "$SRC/tests" "$DEST/"
for f in LICENSE CHANGELOG README.rst README.md; do
  [ -f "$SRC/$f" ] && cp "$SRC/$f" "$DEST/"
done
```
Expected: `pyproject.toml`, `src/covid_time/`, and `tests/` now exist in the repo root. The existing `.gitignore`, `docs/`, and `.git` are untouched.

- [ ] **Step 3: Confirm the scaffold is a Toga app**

```bash
grep -q "import toga" /Users/kattni/BeeWare/covid_time/src/covid_time/app.py && echo "toga app OK" || echo "NOT a toga app"
```
Expected: `toga app OK`. (If it prints `NOT a toga app`, the non-interactive wizard picked the wrong bootstrap — rerun Step 1 interactively and choose **Toga** when asked for the GUI toolkit.)

- [ ] **Step 4: Remove the generated sample test**

The scaffold ships a placeholder test that imports the placeholder app (and transitively Toga). We don't want it:
```bash
rm -f /Users/kattni/BeeWare/covid_time/tests/test_app.py
```

- [ ] **Step 5: Create `conftest.py` so pytest can import `covid_time`**

Create `/Users/kattni/BeeWare/covid_time/conftest.py` with:
```python
import sys
from pathlib import Path

# Make the src/ layout importable under pytest without an editable install.
sys.path.insert(0, str(Path(__file__).parent / "src"))
```

- [ ] **Step 6: Verify the package is importable**

```bash
PYTHONPATH=src .venv/bin/python -c "import covid_time, covid_time.app; print('package OK')"
```
Expected: `package OK` — confirms the `src/` layout resolves. (`conftest.py` does this same `sys.path` insertion automatically under pytest.)

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: scaffold Briefcase/Toga project

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: Implement `day_number()` (TDD)

**Files:**
- Create: `tests/test_clock.py`
- Create: `src/covid_time/clock.py`

- [ ] **Step 1: Write the failing tests**

Create `/Users/kattni/BeeWare/covid_time/tests/test_clock.py` with:
```python
"""Tests for the COVID-time clock logic (no GUI)."""
import datetime
import time

from covid_time.clock import EPOCH, day_number


def _struct(year, month, day, weekday):
    """Build a struct_time. weekday: Mon=0 .. Sun=6 (matches date.weekday())."""
    return time.struct_time((year, month, day, 0, 0, 0, weekday, 0, -1))


def test_day_number_at_epoch_is_one():
    # 2020-03-01 was a Sunday (tm_wday 6).
    assert day_number(_struct(2020, 3, 1, 6)) == 1


def test_day_number_one_month_later():
    # 2020-03-01 -> 2020-04-01 is 31 days; +1 => 32.
    assert day_number(_struct(2020, 4, 1, 2)) == 32


def test_day_number_at_day_two():
    assert day_number(_struct(2020, 3, 2, 0)) == 2


def test_day_number_today_matches_formula():
    today = datetime.date.today()
    now = _struct(today.year, today.month, today.day, today.weekday())
    assert day_number(now) == (today - EPOCH).days + 1
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
.venv/bin/pytest tests/test_clock.py -v
```
Expected: **FAIL** — `ModuleNotFoundError: No module named 'covid_time.clock'` (the module does not exist yet).

- [ ] **Step 3: Implement `day_number()`**

Create `/Users/kattni/BeeWare/covid_time/src/covid_time/clock.py` with:
```python
"""COVID time: the date is always March 2020; only the day count advances."""
import datetime
import time

EPOCH = datetime.date(2020, 3, 1)


def day_number(now=None):
    """Days into eternal March 2020. 2020-03-01 -> 1.

    Args:
        now: A ``time.struct_time``. Defaults to the current local time.
    """
    if now is None:
        now = time.localtime()
    today = datetime.date(now.tm_year, now.tm_mon, now.tm_mday)
    return (today - EPOCH).days + 1
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
.venv/bin/pytest tests/test_clock.py -v
```
Expected: **PASS** (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/covid_time/clock.py tests/test_clock.py
git commit -m "feat: add day_number() clock logic with tests

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: Implement `covid_time_string()` (TDD)

**Files:**
- Modify: `tests/test_clock.py`
- Modify: `src/covid_time/clock.py`

- [ ] **Step 1: Add the failing tests**

In `tests/test_clock.py`, change the import line to also import `covid_time_string`:
```python
from covid_time.clock import EPOCH, covid_time_string, day_number
```
Then append these tests at the end of the file:
```python
def test_covid_time_string_at_epoch():
    s = covid_time_string(_struct(2020, 3, 1, 6))  # Sunday, day 1
    assert s.startswith("Sun Mar 1 ")
    assert s.endswith(" 2020")


def test_covid_time_string_advances_day_number():
    s = covid_time_string(_struct(2020, 4, 1, 2))  # Wednesday, day 32
    assert s.startswith("Wed Mar 32 ")
    assert s.endswith(" 2020")


def test_covid_time_string_carries_time():
    now = time.struct_time((2020, 3, 1, 13, 42, 7, 6, 0, -1))
    assert "13:42:07" in covid_time_string(now)
```

- [ ] **Step 2: Run the tests to confirm the new ones fail**

```bash
.venv/bin/pytest tests/test_clock.py -v
```
Expected: **FAIL** — `ImportError: cannot import name 'covid_time_string'`.

- [ ] **Step 3: Implement `covid_time_string()`**

Append to `/Users/kattni/BeeWare/covid_time/src/covid_time/clock.py`:
```python
def covid_time_string(now=None):
    """The COVID-time line, e.g. ``Sun Mar 2298 13:42:07 EDT 2020``.

    The weekday, time-of-day and timezone are real; only the date is frozen
    at "March 2020" with a climbing day number. ``now`` is a
    ``time.struct_time`` defaulting to the current local time.
    """
    if now is None:
        now = time.localtime()
    weekday = time.strftime("%a", now)
    clock = time.strftime("%H:%M:%S", now)
    zone = time.strftime("%Z", now)
    return f"{weekday} Mar {day_number(now)} {clock} {zone} 2020"
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
.venv/bin/pytest tests/test_clock.py -v
```
Expected: **PASS** (7 tests).

- [ ] **Step 5: Commit**

```bash
git add src/covid_time/clock.py tests/test_clock.py
git commit -m "feat: add covid_time_string() with tests

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: Build the Toga UI and wire up the live tick

This task is verified by running the app (no GUI unit tests — the UI has no branching logic). Per the design, the tick uses `async def on_running()` because `App.add_background_task()` is deprecated and `startup()` cannot be async.

**Files:**
- Modify: `src/covid_time/app.py` (replace the scaffolded placeholder)

- [ ] **Step 1: Replace `app.py` with the implementation**

Overwrite `/Users/kattni/BeeWare/covid_time/src/covid_time/app.py` with:
```python
"""COVID Time — a clock stuck in March 2020."""
import asyncio

import toga
from toga.style import Pack

from .clock import covid_time_string, day_number


class CovidTimeApp(toga.App):
    def startup(self):
        self.day_label = toga.Label(
            f"Day {day_number()}",
            style=Pack(font_size=56, font_weight="bold", text_align="center"),
        )
        self.subtitle_label = toga.Label(
            "of March 2020",
            style=Pack(font_size=16, text_align="center"),
        )
        self.time_label = toga.Label(
            covid_time_string(),
            style=Pack(font_size=18, font_family="monospace", text_align="center"),
        )
        main_box = toga.Box(
            children=[self.day_label, self.subtitle_label, self.time_label],
            style=Pack(
                direction="column",
                align_items="center",
                justify_content="center",
            ),
        )
        self.main_window = toga.MainWindow(size=(360, 240), resizable=False)
        self.main_window.content = main_box
        self.main_window.show()

    def _refresh(self):
        self.day_label.text = f"Day {day_number()}"
        self.time_label.text = covid_time_string()

    async def on_running(self):
        # Fires once the event loop is up. Each await yields control back to
        # the loop, so the UI stays responsive while the clock ticks.
        while True:
            self._refresh()
            await asyncio.sleep(1)


def main():
    return CovidTimeApp(
        formal_name="COVID Time",
        app_id="com.kattni.covidtime",
    )
```

- [ ] **Step 2: Confirm `__main__.py` launches the app**

```bash
cat /Users/kattni/BeeWare/covid_time/src/covid_time/__main__.py
```
Expected: it contains `from covid_time.app import main` and calls `main().main_loop()`. (The scaffolded file already does this; no change needed.)

- [ ] **Step 3: Run the app with Briefcase**

```bash
.venv/bin/briefcase dev
```
Expected (manual check): a **360×240, non-resizable** window titled "COVID Time" appears showing:
- a large `Day <N>` (today's count)
- `of March 2020` beneath it
- the COVID-time line (e.g. `Sun Mar 2298 13:42:07 EDT 2020`)

The seconds advance every ~1 second. Close the window to exit.

- [ ] **Step 4: Commit**

```bash
git add src/covid_time/app.py
git commit -m "feat: add COVID Time Toga UI with live on_running tick

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: Verify local macOS packaging

This confirms the "distributable" goal locally. Producing Windows/Linux binaries is deferred to a future CI plan.

**Files:** none committed (build artifacts under `macOS/`, `dist/`, both gitignored).

> Requires Xcode Command Line Tools (`xcode-select -p`). If missing, install via `xcode-select --install` (run manually — it's interactive).

- [ ] **Step 1: Create the Briefcase binary stub**

```bash
.venv/bin/briefcase create
```
Expected: completes with no errors; a `macOS/` directory is created.

- [ ] **Step 2: Build the app**

```bash
.venv/bin/briefcase build
```
Expected: completes with no errors; `macOS/COVID Time/COVID Time.app` exists.

- [ ] **Step 3: Package it (ad-hoc signed, no Apple developer account needed)**

```bash
.venv/bin/briefcase package --adhoc-sign
```
Expected: a `.dmg` is produced under `dist/` (e.g. `dist/COVID Time-0.0.1.dmg`). If `--adhoc-sign` is rejected by your Briefcase version, drop the flag (an unsigned `.app` still launches locally).

- [ ] **Step 4: Launch the packaged app and confirm it runs**

Open `macOS/COVID Time/COVID Time.app` (or mount the `.dmg` and open the app inside):
```bash
open "macOS/COVID Time/COVID Time.app"
```
Expected: the same COVID Time window appears and ticks, independent of `briefcase dev`.

---

## Notes & deliberate deviations from the spec

- **Window centering:** the spec says "centered," but Toga does not center windows by default and computing a centered position adds platform-specific complexity for little gain. The plan lets the OS place the window. (To center later: set `self.main_window.position` from `self.app.screens[0].size` in `startup`.)
- **`app_id`:** runtime uses `com.kattni.covidtime`; Briefcase packaging derives its identifier from `bundle` (`com.kattni`) + `app_name` (`covid_time`). The minor difference is harmless and consistent with the design.
- **`conftest.py`:** added so pytest imports the `src/` layout without an editable install, regardless of what the scaffold's `pyproject.toml` configures.
- **Deferred to a future plan:** the GitHub Actions matrix that builds Windows/Linux binaries on those OSes (each platform's bundle must be built natively).
