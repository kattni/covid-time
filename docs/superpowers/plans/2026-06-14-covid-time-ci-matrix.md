# COVID Time CI Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A GitHub Actions workflow that, on a version tag (`v*`), builds and packages COVID Time natively on macOS, Windows, and Linux runners, and uploads each platform's installer as a build artifact.

**Architecture:** A single `build` job using a 3-way OS matrix (`macos-latest`, `windows-latest`, `ubuntu-latest`). Each runner checks out the repo, sets up Python, installs Briefcase, then runs `briefcase create` → `build` → `package` with a per-OS packaging format and the non-interactive signing flag, then uploads `dist/*`. Each OS builds its own binary natively — the one hard rule of cross-platform packaging.

**Tech Stack:** GitHub Actions, Briefcase 0.4.x, Python 3.12 (CI-stable; the app is pure Python).

**Design spec:** [`docs/superpowers/specs/2026-06-14-covid-time-design.md`](../specs/2026-06-14-covid-time-design.md) — this implements the "Follow-on" cross-platform distribution goal.

---

## File Structure

| Path | Responsibility |
|---|---|
| `.github/workflows/release.yml` | The release matrix workflow |

This is the only file the plan adds.

## Key gotchas baked into the workflow

1. **`python -m briefcase`** (not bare `briefcase`) so the command resolves identically on Windows (no PATH surprises).
2. **macOS needs an explicit signing flag.** `briefcase package` prompts interactively for a signing identity (and aborts with no stdin on CI). Use `--adhoc-sign` so it runs unattended. (Ad-hoc = runs only on the building machine; see "Signing & distribution" below.)
3. **Linux needs a non-interactive format + GTK system libraries.** `briefcase package` would prompt to choose a format on Linux, so pass `-p appimage`. Toga on Linux uses GTK, so the runner needs GTK dev headers installed via `apt` *before* `briefcase create`.
4. **Python 3.12 on CI**, not the local 3.14 — broader runner availability; the app is version-agnostic.

---

## Task 1: Add the release workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [x] **Step 1: Create the workflow file**

Create `/Users/kattni/BeeWare/covid_time/.github/workflows/release.yml` with:

```yaml
name: Release

on:
  push:
    tags:
      - "v*"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  build:
    name: Package (${{ matrix.os }})
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: macos-latest
            package_args: "--adhoc-sign"
          - os: windows-latest
            package_args: ""
          - os: ubuntu-latest
            package_args: "-p appimage"
    runs-on: ${{ matrix.os }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Briefcase
        run: python -m pip install briefcase

      - name: Install Linux system dependencies (GTK)
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            libgirepository1.0-dev \
            libcairo2-dev \
            libpango1.0-dev \
            libgdk-pixbuf2.0-dev \
            pkg-config \
            gir1.2-gtk-3.0

      - name: briefcase create
        run: python -m briefcase create

      - name: briefcase build
        run: python -m briefcase build

      - name: briefcase package
        shell: bash
        run: python -m briefcase package ${{ matrix.package_args }}

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: COVID-Time-${{ matrix.os }}
          path: dist/*
          if-no-files-found: error
```

- [x] **Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add cross-platform release workflow (macOS/Windows/Linux)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Trigger a test run

CI can't be exercised locally — it runs only when the workflow file is on a branch of a GitHub repo. This task is therefore a manual trigger done after the repo is pushed to GitHub.

**Prerequisite:** the repo must be pushed to GitHub (`git remote add origin <url> && git push -u origin main`).

- [ ] **Step 1: Push to GitHub (if not already)**

```bash
# create an empty repo on GitHub first, then:
git remote add origin <YOUR_GIT_URL>
git push -u origin main
```

- [ ] **Step 2: Trigger via `workflow_dispatch` (no tag needed yet)**

On GitHub: **Actions → Release → Run workflow** (uses the `workflow_dispatch` trigger). This runs all three matrix legs immediately so you can see failures without cutting a tag.

- [ ] **Step 3: Watch each matrix leg go green**

Expected: three jobs (macOS/Windows/Linux) each reach "Upload artifacts." If a leg fails, see the per-leg fixes below.

**Per-leg troubleshooting (first run is likely to need one of these):**
- **Linux fails at `briefcase create`/`build`** → a GTK header is missing; add it to the `apt-get install` list (consult `briefcase`'s Linux system-requirements docs for the exact package set for your Toga version).
- **macOS fails at `briefcase package`** → it prompted for signing; confirm `--adhoc-sign` is in `matrix.package_args` for the macOS row.
- **Windows fails at `briefcase package`** → if it prompts for a signing identity, change the Windows row to `package_args: "--no-sign"` (or set up a code-signing cert — see below).

---

## Task 3: Cut a real release tag

Once all three legs are green via `workflow_dispatch`:

- [ ] **Step 1: Tag and push**

```bash
git tag v0.0.1
git push origin v0.0.1
```

- [ ] **Step 2: Download the artifacts from the run**

Expected: three artifacts (`COVID-Time-macos-latest`, `COVID-Time-windows-latest`, `COVID-Time-ubuntu-latest`), each containing the platform's installer (`COVID Time-0.0.1.dmg` / `.msi` / `.AppImage`).

---

## Signing & distribution (deferred — not in this plan)

The workflow produces **ad-hoc / unsigned** builds: they run on the machine that built them but **not** on other people's machines (and macOS will block an unsigned `.dmg` via Gatekeeper). Truly redistributable builds require, per platform:

- **macOS:** an Apple Developer ID Application certificate + notarization. Store the identity name and App Store Connect credentials as repo secrets, then swap `--adhoc-sign` for `--identity "$APPLE_SIGNING_IDENTITY"` and add `--notarize` (Briefcase reads `APPLE_*` env vars for notarization).
- **Windows:** a code-signing certificate; pass `--identity` to `briefcase package`.
- **Linux:** AppImage needs no signing; Flatpak/Snap (if preferred over AppImage) are signed through their respective store accounts.

These are deliberately left for a follow-up once the unsigned CI matrix is green and distribution scope is confirmed.

## Auto-attaching to a GitHub Release (optional enhancement)

To attach artifacts to the `v*` tag's Release automatically, add a final job (after `build`) using `softprops/action-gh-release` with `actions/download-artifact`. Not required for the MVP CI goal (artifact download from the Actions run is sufficient) — include only if you want the "Releases" page populated.
