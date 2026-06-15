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
2. **macOS signs + notarizes with a real Developer ID identity.** A "Set up macOS code-signing & notarization" step (macOS-only) imports the `MACOS_CERTIFICATE` (`.p12`, base64) into a dedicated keychain, grants `codesign` access via `set-key-partition-list`, and stores the App Store Connect API key as the `notarytool` profile `briefcase-macOS-<APPLE_TEAM_ID>`. The package step uses `--identity "$APPLE_SIGNING_IDENTITY"`, and Briefcase auto-notarizes via that profile. (The earlier `--adhoc-sign` fallback produced apps that ran only on the build machine.)
3. **Linux Flatpak is a positional *format*, selected on every command — not `-p`.** Briefcase's syntax is `briefcase <command> <platform> <format>`; the linux formats are `appimage`/`flatpak`/`system` (default `system`). Select the Flatpak backend by passing it positionally on **all of create, build, and package** — `briefcase create linux flatpak`, `… build linux flatpak`, `… package linux flatpak` — otherwise create/build default to `system` and `package -p flatpak` is rejected (`-p`/`--packaging-format` is a separate output-bundle axis: deb/rpm/pkg/system for the system backend). The runner also needs `flatpak` + `flatpak-builder` **and** the GTK dev headers (`gir1.2-gtk-3.0 libcairo2-dev libcanberra-gtk3-module libgirepository1.0-dev`) — Briefcase's Linux `create` verifies these on the host regardless of format, even though the Flatpak build itself runs inside the `org.gnome.Sdk` sandbox. Briefcase registers the Flathub remote and pulls the runtime itself. (Flatpak cannot be built inside a Docker container — `ubuntu-latest` runs jobs on the bare VM, so this is fine.)
4. **Python 3.12 on CI**, not the local 3.14 — broader runner availability; the app is version-agnostic.
5. **Linux must run Briefcase under the system python3.** Briefcase's Linux backend aborts `briefcase create` (exit code 200) if the interpreter running it isn't the system `python3`. `actions/setup-python` installs a *different* patch version (e.g. 3.12.13 vs the runner's system 3.12.3), so the workflow skips setup-python on Linux and installs Briefcase with `pipx --python /usr/bin/python3` instead. macOS/Windows have no such guard.

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
            package_args: "-p flatpak"
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

      - name: Install Linux system dependencies (Flatpak)
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y flatpak flatpak-builder

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

- [x] **Step 1: Push to GitHub (if not already)**

```bash
# create an empty repo on GitHub first, then:
git remote add origin <YOUR_GIT_URL>
git push -u origin main
```

- [x] **Step 2: Trigger via `workflow_dispatch` (no tag needed yet)**

On GitHub: **Actions → Release → Run workflow** (uses the `workflow_dispatch` trigger). This runs all three matrix legs immediately so you can see failures without cutting a tag.

- [x] **Step 3: Watch each matrix leg go green**

Expected: three jobs (macOS/Windows/Linux) each reach "Upload artifacts." If a leg fails, see the per-leg fixes below.

**Per-leg troubleshooting (first run is likely to need one of these):**
- **Linux fails at `briefcase create` with exit 200 ("… is not the system python3")** → the system-python3 setup regressed; confirm `Set up Python` is skipped on Linux (`if: runner.os != 'Linux'`) and Briefcase is installed via `pipx --python /usr/bin/python3`.
- **Linux fails at `briefcase create` with "missing system dependencies"** → Briefcase prints the exact `sudo apt install …` line it needs (GTK dev headers); add those packages to the "Install Linux system dependencies" step and re-run. This fires even for the Flatpak target, because `create` runs the Linux host verification regardless of format.
- **Linux fails at `briefcase package` with "invalid choice: 'flatpak' (choose from deb/rpm/pkg/system)"** → the Flatpak backend wasn't selected; `flatpak` must be the positional format on create/build/package (`briefcase … linux flatpak`), not `-p flatpak`.
- **Linux fails later in `briefcase build`/`package`** → if it can't find a runtime, the `org.gnome.Platform`/`Sdk` **48** runtime may not be on Flathub yet — bump `flatpak_runtime_version` in `pyproject.toml` and re-run. If it fails on icons, Flatpak requires PNG icons (16–512px); add a source `.png` to `src/covid_time/resources/` and let Briefcase generate the sizes.
- **macOS fails at `briefcase package`** → it prompted for signing; confirm `--adhoc-sign` is in `matrix.package_args` for the macOS row.
- **Windows fails at `briefcase package`** → if it prompts for a signing identity, change the Windows row to `package_args: "--no-sign"` (or set up a code-signing cert — see below).

---

## Task 3: Cut a real release tag

Once all three legs are green via `workflow_dispatch`:

- [x] **Step 1: Tag and push**

```bash
git tag v0.0.1
git push origin v0.0.1
```

- [x] **Step 2: Download the artifacts from the run**

Expected: three artifacts (`COVID-Time-macos-latest`, `COVID-Time-windows-latest`, `COVID-Time-ubuntu-latest`), each containing the platform's installer (`COVID Time-0.0.1.dmg` / `.msi` / `COVID_Time-0.0.1-x86_64.flatpak`).

---

## Signing & distribution

The macOS build is **signed + notarized** (redistributable). Windows and Linux are still **unsigned** — the Linux Flatpak bundle installs fine via `flatpak install --user`, but Windows (and any macOS run without the signing secrets) only works on the build machine. Status per platform:

- **macOS:** ✅ implemented. The Developer ID Application certificate (`.p12`, base64 in `MACOS_CERTIFICATE`) is imported into a CI keychain and the App Store Connect API key (`APP_STORE_CONNECT_API_KEY` / `_ID` / `_ISSUER`) is stored as the `briefcase-macOS-<APPLE_TEAM_ID>` notarytool profile; `briefcase package` runs with `--identity "$APPLE_SIGNING_IDENTITY"` and Briefcase notarizes automatically. (Briefcase 0.4.2 notarizes by default whenever a real identity is used — there is no `--notarize` flag; `--no-notarize` opts out.)
- **Windows:** a code-signing certificate; pass `--identity` to `briefcase package`.
- **Linux:** the Flatpak `.flatpak` bundle is unsigned but installable directly with `flatpak install --user <bundle>`. For wide distribution, publish to Flathub, which handles signing via your Flathub account. AppImage/Snap are alternatives, each with its own signing model.

Windows code-signing and Flathub publishing remain follow-ups; the macOS signing step is in place and the CI matrix is green.

## Auto-attaching to a GitHub Release (implemented)

A `release` job runs after `build` (on `ubuntu-latest`, `needs: build` so a partial build never ships). It downloads all three OS artifacts with `actions/download-artifact@v4` (`merge-multiple`) and creates a GitHub Release via `softprops/action-gh-release@v2`, attaching the `.dmg`, the Windows installer, and the `.flatpak`.

Two-trigger behavior:
- **`push: v*` tag** → published Release on that tag, with GitHub auto-generated release notes.
- **`workflow_dispatch`** → **prerelease** with a generated tag `ci-<run_number>`, so manual test runs don't clutter the Releases page as real ships.

The per-run `upload-artifact` step remains — the `release` job downloads from those same artifacts.
