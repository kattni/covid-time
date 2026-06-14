# COVID Time — Design

**Date:** 2026-06-14
**Status:** Approved (pending implementation plan)

## Overview

A small native desktop app — built with BeeWare (Toga for UI, Briefcase for packaging) — that displays "COVID time": the **real** weekday, time-of-day, and timezone, but with the **date frozen at "March 2020."** The day number is the count of days since 2020-03-01, so it keeps climbing (`Mar 2298`, `Mar 2299`, …). It's a joke about how March 2020 never really ended.

The concept comes from [jepler's `covidtime.py`](https://codeberg.org/jepler/junkdrawer/src/branch/main/d0a6j6ey/covidtime.py) snippet, which prints a single line:

```
Sun Mar 2298 13:42:07 EDT 2020
```

## Goals & scope

- **Primary goal:** a *distributable* app — styled, packaged, installable by others. Not a throwaway.
- **Target platforms:** macOS, Windows, and Linux desktops (BeeWare's cross-platform pitch).
- **Display:** the COVID-time timestamp **plus** a prominent "Day NNNN of March 2020" counter.
- **Live updating:** the clock ticks every second; the day number rolls over at local midnight.

## Out of scope (deliberately deferred)

- iOS / Android. Mobile UI patterns and Toga's mobile maturity aren't worth it for a joke clock.
- macOS code-signing and notarization. A real time-sink; not required for a fun distributable. Revisit if sharing broadly or hitting Gatekeeper friction.
- Any App Store presence.
- Persisted window state (position/size), settings, or configuration. The window is stateless.
- Network features, accounts, or telemetry. None needed.

## Architecture

**Approach:** idiomatic Briefcase + Toga, with the time math split into a pure, injectable module that is unit-testable independent of any GUI.

The time logic (the heart of the joke) is isolated from the UI. `clock.py` has no Toga import; `app.py` has no date math. This lets us test "2020-03-01 → Day 1" and "today → Day NNNN" without spinning up a window, and keeps the UI a thin shell.

### Project structure

```
covid_time/
├── pyproject.toml              # Briefcase config: app "COVID Time", bundle com.kattni.covidtime
├── README.md
├── LICENSE
├── CHANGELOG
├── tests/
│   ├── __init__.py
│   └── test_clock.py           # unit tests for the time math (no GUI)
└── src/covid_time/
    ├── __init__.py
    ├── __main__.py             # `python -m covid_time` entry
    ├── app.py                  # Toga App + MainWindow (UI only)
    └── clock.py                # pure functions — the snippet, refactored & injectable
```

The single runtime dependency is **Toga**, pinned and managed via Briefcase in `pyproject.toml`.

### `clock.py` — the time math

The snippet, wrapped as pure functions with an injectable `now` (defaults to `time.localtime()`) so tests are deterministic:

```python
import datetime
import time

EPOCH = datetime.date(2020, 3, 1)

def day_number(now=None):
    """Days since 2020-03-01, plus one. 2020-03-01 -> 1."""
    now = now or time.localtime()
    today = datetime.date(now.tm_year, now.tm_mon, now.tm_mday)
    return (today - EPOCH).days + 1

def covid_time_string(now=None):
    """The COVID-time line, e.g. 'Sun Mar 2298 13:42:07 EDT 2020'."""
    now = now or time.localtime()
    wday = time.strftime("%a", now)
    hms = time.strftime("%H:%M:%S", now)
    tz = time.strftime("%Z", now)
    return f"{wday} Mar {day_number(now)} {hms} {tz} 2020"
```

The `"Mar 2298"` overflow (day count climbing past 31) is the joke and is **preserved verbatim** — never "corrected" into real calendar dates.

### `app.py` — the UI

A Toga `App` with a `startup()` that builds and shows a single `MainWindow`.

- **Window:** titled "COVID Time", fixed at roughly **360×240**, **centered**, **non-resizable**. A small, stable frame suits a clock.
- **Layout:** a vertical `Box`, content centered:
  - **Hero label** (≈56pt, bold): `Day 2298`
  - **Subtitle** (smaller, muted): `of March 2020`
  - **COVID-time string** (monospace, medium): `Sun Mar 2298 13:42:07 EDT 2020`

**Live tick** — `on_running()`, an async lifecycle hook that fires once the app's event loop is up (unlike `startup()`, it can be async; `App.add_background_task()` is deprecated in current Toga):

```python
def startup(self):
    # build main_box with the labels…
    self.main_window.content = main_box
    self.main_window.show()

async def on_running(self):
    # on_running() fires once the event loop is up; unlike startup() it CAN
    # be async. (App.add_background_task is deprecated in current Toga.)
    while True:
        self._refresh()          # reads clock.py, updates both labels
        await asyncio.sleep(1)
```

`_refresh()` calls `day_number()` and `covid_time_string()` and updates the labels. Because the coroutine runs on Toga's asyncio loop (not a separate OS thread), UI updates are thread-safe with no locking.

### Data flow

```
Toga asyncio loop
      │  every 1s
      ▼
on_running() ──► _refresh() ──► clock.day_number(now) ──► hero label text
                          └► clock.covid_time_string(now) ──► timestamp label text
```

`now` defaults to the current local time at each tick. No state is held between ticks; each refresh recomputes from scratch.

## Testing

`pytest`, focused on `clock.py`. The injectable `now` (a `time.struct_time`) makes every test deterministic — no monkeypatching of `time.time`.

- `day_number(struct_time(2020, 3, 1))` → `1` (the anchor / epoch).
- `day_number(struct_time(2020, 4, 1))` → `32` (mid-range known value).
- `day_number(struct_time(today))` → equals `(today − EPOCH).days + 1`.
- `covid_time_string(struct_time(2020, 3, 1))` → contains `"Mar"`, `" 2020"`, and the injected weekday, with day number `1`.
- `covid_time_string(struct_time(today))` → day number matches `day_number(today)`.

No GUI tests. The UI has no branching logic — `_refresh` copies computed values into labels — so the unit tests on `clock.py` fully cover the meaningful behavior.

## Error handling

Intentionally minimal, by design.

`time.localtime()` and integer date arithmetic have no meaningful failure modes. There is no network, no filesystem, no persistence, and no configuration. Therefore: **no defensive `try/except`.** If `clock.py` ever raises, that is a bug to surface, not swallow. The tick loop stays a plain `while True`; if it ever raises, the app fails loudly rather than silently freezing.

## Packaging & distribution

**MVP (local):**

- `briefcase dev` to run the app during development.
- `briefcase package macOS` to build a local `.app` / `.dmg`.
- `pytest` green.

**Follow-on (the cross-platform distribution goal):**

A **GitHub Actions matrix** — `macos-latest`, `windows-latest`, `ubuntu-latest` — where each runner runs `briefcase package` on its own OS (each platform's bundle must be built on that OS). Artifacts:

- macOS → `.dmg` (unsigned)
- Windows → `.msi` (or `.zip`)
- Linux → AppImage (primary); Flatpak optional

Triggered on a version tag; binaries attached to the corresponding GitHub Release.

## Decisions log

| Decision | Choice | Why |
|---|---|---|
| Architecture | Split clock logic from UI (Approach 1) | Time math is testable in isolation; UI is a thin shell |
| Live tick | asyncio background task on Toga's loop | Thread-safe by construction; idiomatic modern Toga |
| Platforms | macOS, Windows, Linux desktop | Leans into BeeWare's cross-platform strength |
| Day overflow | Preserve `"Mar 2298"` verbatim | It's the joke |
| GUI tests | None | No branching logic in the UI to cover |
| Signing/notarization | Deferred | Not worth the time-sink for a fun distributable |
