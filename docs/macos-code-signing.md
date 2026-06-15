# Adding Apple code-signing & notarization to release CI

This document explains how the COVID Time release pipeline signs and notarizes the
macOS `.dmg` so it runs on other people's Macs — not just the build machine. It's
both a reference for the setup already in `.github/workflows/release.yml` and a
recipe for reproducing it in another Briefcase project.

## Background: what "works for others" requires

Two separate Apple checks gate a distributable macOS app:

1. **Code-signing** with a *Developer ID Application* certificate — clears
   Gatekeeper's "unidentified developer" block.
2. **Notarization** — Apple scans the app, issues a ticket, and the ticket is
   stapled on — Gatekeeper then shows the green "Apple checked it for malicious
   software" result.

Briefcase 0.4.x does **both automatically** when you sign with a real identity —
it only skips notarization for `--adhoc-sign`. Notarization is performed with
`xcrun notarytool submit --keychain-profile briefcase-macOS-<TEAM_ID>`, so CI has
two jobs: (a) put the signing certificate in the keychain, and (b) populate that
exact keychain profile with notarization credentials.

## Prerequisites (one-time, on your Apple account)

| Artifact | How to get it |
|---|---|
| Apple Developer Program membership | $99/yr at developer.apple.com |
| **Developer ID Application** certificate + private key | developer.apple.com → Certificates, IDs & Profiles → create a "Developer ID Application" cert. Export from Keychain Access as a **`.p12`** with a password. |
| **App Store Connect API key** (`.p8`) | App Store Connect → Users and Access → Keys → generate a key (App Manager or Developer role). Download the `.p8`; note the **Key ID** and **Issuer ID**. |
| **Team ID** | 10-char code on your developer account; also appears in the certificate name's parentheses. |

Use the **App Store Connect API key** auth method (not Apple ID + an app-specific
password): it's fully non-interactive and 2FA-free, which is exactly what CI needs.

## Add the GitHub repo secrets

| Secret | Value |
|---|---|
| `MACOS_CERTIFICATE` | base64 of the `.p12` — `base64 -i cert.p12 \| pbcopy` |
| `MACOS_CERTIFICATE_PWD` | the `.p12` password |
| `APPLE_SIGNING_IDENTITY` | `Developer ID Application: Your Name (TEAMID)` — exactly as it appears in Keychain |
| `APPLE_TEAM_ID` | the 10-char Team ID — **must equal** the parenthetical in `APPLE_SIGNING_IDENTITY` |
| `APP_STORE_CONNECT_API_KEY` | base64 of the `.p8` file |
| `APP_STORE_CONNECT_API_KEY_ID` | the Key ID |
| `APP_STORE_CONNECT_API_KEY_ISSUER` | the Issuer ID |

> **Consistency check (the most common failure):** `APPLE_TEAM_ID` must equal the
> team ID inside `APPLE_SIGNING_IDENTITY`'s parentheses. Briefcase derives the team
> ID from the identity name and looks for a profile named
> `briefcase-macOS-<team_id>`; the workflow stores the profile as
> `briefcase-macOS-$APPLE_TEAM_ID`. A mismatch → notarytool fails with
> "keychain profile not found."

## The workflow

### 1. Set up signing & notarization (macOS-only step, before `briefcase package`)

```yaml
      - name: Set up macOS code-signing & notarization
        if: runner.os == 'macOS'
        env:
          MACOS_CERTIFICATE: ${{ secrets.MACOS_CERTIFICATE }}
          MACOS_CERTIFICATE_PWD: ${{ secrets.MACOS_CERTIFICATE_PWD }}
          APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
          ASC_API_KEY: ${{ secrets.APP_STORE_CONNECT_API_KEY }}
          ASC_API_KEY_ID: ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }}
          ASC_API_KEY_ISSUER: ${{ secrets.APP_STORE_CONNECT_API_KEY_ISSUER }}
        run: |
          KC="$RUNNER_TEMP/signing.keychain-db"
          KCPW="$(uuidgen)"
          security create-keychain -p "$KCPW" "$KC"
          security set-keychain-settings -lut 21600 "$KC"
          security unlock-keychain -p "$KCPW" "$KC"

          echo "$MACOS_CERTIFICATE" | base64 -D -o "$RUNNER_TEMP/cert.p12"
          security import "$RUNNER_TEMP/cert.p12" -P "$MACOS_CERTIFICATE_PWD" -A -t cert -f pkcs12 -k "$KC"
          security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$KCPW" "$KC"

          security list-keychains -d user -s "$KC" login.keychain-db
          security default-keychain -d user -s "$KC"

          echo "$ASC_API_KEY" | base64 -D -o "$RUNNER_TEMP/AuthKey.p8"
          xcrun notarytool store-credentials "briefcase-macOS-$APPLE_TEAM_ID" \
            --key "$RUNNER_TEMP/AuthKey.p8" \
            --key-id "$ASC_API_KEY_ID" \
            --issuer "$ASC_API_KEY_ISSUER" \
            --keychain "$KC"
```

### 2. Package with the real identity instead of `--adhoc-sign`

```yaml
      - name: briefcase package
        shell: bash
        env:
          APPLE_SIGNING_IDENTITY: ${{ secrets.APPLE_SIGNING_IDENTITY }}
        run: python -m briefcase package --identity "$APPLE_SIGNING_IDENTITY"
```

Briefcase then signs with that identity and notarizes automatically using the
`briefcase-macOS-<team_id>` profile. (In 0.4.x there is no `--notarize` flag —
notarization is the default whenever a real identity is used; `--no-notarize`
opts out.)

## What each part of the keychain setup does

- **`create-keychain`** — makes a dedicated keychain so the cert is isolated from
  the runner's default login keychain.
- **`set-keychain-settings -lut 21600`** — sets a 6-hour auto-lock window so the
  keychain stays unlocked through a long build + notarization wait. Without it the
  keychain can auto-lock mid-job, and `codesign` fails with no GUI to re-unlock.
- **`import … -A`** — imports the `.p12`; `-A` allows any app to use the private
  key without prompting.
- **`set-key-partition-list -S apple-tool:,apple:,codesign: -s`** — the fix for CI
  `codesign` failing with *"User interaction is not allowed."* macOS keys carry an
  access-control partition list; even with `-A` on import, `codesign` isn't on it
  until this adds the `codesign:` partition (plus the `apple`/`apple-tool`
  partitions `notarytool` uses). `-s` targets signing-capable keys.
- **`default-keychain` + `list-keychains`** — make this keychain the default and
  put it in the search list so `codesign` finds the identity and `notarytool` finds
  the stored profile.
- **`notarytool store-credentials`** — stores the App Store Connect API key under
  the profile name `briefcase-macOS-<team_id>` non-interactively. Briefcase's
  later `notarytool submit --keychain-profile …` reads this profile. `base64 -D`
  is BSD decode (this step runs only on macOS runners); on Linux use `-d`.

## Verify a produced `.dmg`

```sh
# Validates the notarization ticket is stapled to the disk image:
xcrun stapler validate "COVID Time-0.0.1.dmg"     # → "The validate action worked!"

# Deeper check: mount it and inspect the app inside:
hdiutil attach "COVID Time-0.0.1.dmg"
spctl -a -vv "/Volumes/COVID Time/COVID Time.app"   # → "source=Notarized Developer ID"
codesign -dv --verbose=4 "/Volumes/COVID Time/COVID Time.app"
hdiutil detach "/Volumes/COVID Time"
```

Then open it on a Mac that didn't build it — Gatekeeper should not warn.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `codesign` … *"User interaction is not allowed"* | `set-key-partition-list` is missing or lacks the `codesign:` partition — include `-S apple-tool:,apple:,codesign:`. |
| notarytool *"keychain profile not found"* (Briefcase reports a keychain issue) | `APPLE_TEAM_ID` ≠ the team ID in `APPLE_SIGNING_IDENTITY`'s parentheses — make them match. |
| *"no identity found"* / signing identity not matched | `APPLE_SIGNING_IDENTITY` doesn't exactly match the cert name — copy it verbatim, including the `(TEAMID)`. |
| notarytool authentication fails | wrong `.p8` / Key ID / Issuer ID triple — regenerate or re-copy from App Store Connect. |
| Notarization interrupted or the job times out | Briefcase prints a submission ID; resume with `briefcase package --identity "…" --resume <submission-id>`. Notarization can take minutes. |

## Notes & caveats

- **Cost:** requires the paid Apple Developer Program.
- **Secrets are repo-scoped.** Runs triggered by pull requests from forks don't
  receive secrets, so signing only happens on trusted (branch/tag/dispatch) runs.
- **Platform scope:** this covers macOS only. Windows code-signing is a separate
  process (a Windows code-signing certificate passed via `--identity`); Linux
  Flatpak bundles are installed via `flatpak install --user` without signing.
