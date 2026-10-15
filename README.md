# JEV Launcher for Omarchy

Click **JEV** in the bar, or press **Super+Alt+J** if you added the optional shortcut. Describe what you need and press Enter. Clear matches with a reviewed safe operation run automatically. **Preview only** shows the planned operation without running it. Escape or clicking outside closes the overlay.

**Browse actions** / **Ctrl+B** opens the live command catalogue. Type to filter command names, groups, descriptions and aliases. Up/Down selects a row; Enter or clicking inspects it. Inspection fills the command into the request field but does not run it. Add any needed operation/value and press Enter to ask JEV.

The catalogue refreshes on opening the launcher and before every routed request, using `omarchy commands --all --json`. It includes internal helpers, safe adapters for folders/mute/settings panels, and active keyboard shortcuts from `hyprctl -j binds`. Shortcuts show the actual key combination and description, including submap/release context; JEV never presses the keys. Command payloads attached to keybindings are never included in the catalogue or sent to JEV. New commands are discovered without adding phrases or changing the router.

| Label | Meaning |
| --- | --- |
| Runs automatically | Reviewed operation with no parameters. Browser/terminal launches also require the request to contain no URL, search or shell payload. |
| Safe options available | A reviewed adapter can run validated operations/arguments. Other options stay advisory. |
| Keyboard shortcut · information only | Shows the active key combination; never invokes it. |
| Suggestion only | Discoverable and routable, but has no executor. This is the default for new commands. |

Try:

- “My eyes feel tired” / “Øynene mine er slitne” → night light on; “Turn off night light” → neutral colours.
- “Set brightness to 45%” → validated display brightness (5–100%); “too bright/dark” → a 5% step.
- “It is too loud”, “mute the speakers”, “set speaker volume to 35%” → bounded speaker controls.
- “Make the keyboard backlight brighter” → keyboard backlight up.
- “Open Bluetooth settings” / “Open Wi-Fi settings” → open the panel and hand over focus; connection and power changes remain manual.
- “What keyboard shortcut opens the browser?” → show the active binding. Browse also filters shortcuts by keys or description.
- “Mute my microphone” → idempotent mute. Enabling it is suggestion-only.
- “I need my downloads” → Downloads; “open a terminal” → plain terminal window.
- “Remind me to stretch in twenty minutes” → reminder with locally parsed duration and source label.
- “Show my reminders”, “which Omarchy version is installed?”, “list available themes”.
- “Install Spotify”, “remove Minecraft”, “switch theme”, “reboot” → discovered command and manual guidance, no execution.

## Execution boundary

Discovery is separate from permission. `catalogue.py` contains a small explicit table of reviewed operation schemas, not a phrase list. Anything else—including commands reporting `requires_sudo: false`—stays suggestion-only. A privileged command cannot execute automatically even if its name matches a reviewed route. Never infer execution permission from a command group.

`routing.py` first asks JEV for the command group and single/mixed/non-action intent in one request. It then asks for a command from that group and independent branch-specific argument choices in a second request. Every discovered route participates; large groups split below the Choice option limit. The final command/intent/used parameters require probability ≥ 0.90 and confidence ≥ 0.85. Retrieval uses a lower threshold because it does not grant execution permission. Uncertain matches are advisory.

Code builds every argv. The model cannot supply shell commands, paths, executable names or free-form arguments. Brightness and volume have numeric bounds; reminders must use one locally parsed whole-minute duration of 1–1440 minutes and a source-derived label. Missing, ambiguous, fractional and unsupported arguments need clarification. Dates, recurring reminders and arbitrary clock times are not supported. Installed-theme commands are discoverable but remain suggestion-only because applying a theme runs hooks and changes application configuration.

The only automatic operations are the exact reviewed routes in `NO_ARGUMENTS` and `PARAMETERS`, subject to argument validation. Destructive file operations, reset, power/locking/logout, security/network changes, packages, arbitrary code, messages and unreviewed operations have no execution path. Display-off and reminder-clear suboperations stay advisory. Mixed requests do not execute any part.

All subprocess calls use argv arrays, `shell=False`, checked exit status and timeouts. App launchers do not inherit captured output pipes. Read-only results are returned in the overlay; dynamic text is rendered as plain text. Night light reads current and final state so repeated “on” stays on. Requests stop after 60 seconds. Closing the launcher stops waiting but cannot undo an action that already started. A timeout or command failure may still mean a partial change: inspect the desktop before retrying.

Thresholds and live examples are not a correctness guarantee. A model mistake can choose a different permitted harmless operation; the local policy bounds possible effects.

## Privacy and credentials

No background HTTP server, history database or transcript logging. Catalogue browsing works locally without the API. Submitted requests and relevant command metadata are sent to `https://api.typesafe.ai/v1/systemone` using `jev-latest`. No screen, clipboard, file contents or shortcut command payloads are sent. Shortcut descriptions and key combinations are included only as catalogue metadata. If active shortcuts cannot be read outside the graphical session, command discovery still works. Remote processing follows your TypeSafe account's terms. Reminders themselves are intentionally stored by Omarchy until they fire or are cleared manually.

The worker prefers `~/.config/omarchy/jev/api-key`, falling back to `TYPESAFE_API_KEY` only if no saved key exists. The saved key is a user-owned regular file (600) inside a private directory (700). Symlinks, hardlinks, devices, FIFOs, oversized keys and control characters are rejected. HTTP redirects are refused, including redirects to the same host. Credentials never enter QML, command arguments, exception output or repository files. Local commands do not inherit `TYPESAFE_API_KEY`.

Click **Configure key** (or Ctrl+K) to open a hidden terminal prompt. Setup makes a small live connection test before atomically replacing the saved key, so a failed connection keeps the previous key. Setup can repair permissions on owned regular credential files. No credential backups are created. Changing the environment does not override a saved key; rerun setup to rotate it.

The plugin shares your desktop user privileges with other Omarchy plugins. This is not protection against malicious code already running as your user. Read [SECURITY.md](SECURITY.md) for the review scope and limits.

## Install and develop

Use `~/.agents/skills/typesafe-ai/SKILL.md` for JEV work and the Omarchy skill for desktop changes. TypeSafe API documentation: https://docs.typesafe.ai/api. Function-calling and hierarchy patterns: https://docs.typesafe.ai/cookbooks/function_calling and https://docs.typesafe.ai/cookbooks/hierarchical_classification.

Requires a current Omarchy installation with shell plugin support, Python 3.10+ and a TypeSafe API account. Desktop adapters use installed Omarchy commands, `wpctl` and `xdg-open`. No pip/npm packages are required.

Install the public plugin:

```sh
omarchy plugin add https://github.com/Cozidian/omarchy-jev --enable
python3 ~/.config/omarchy/plugins/io.github.cozidian.jev/setup.py
```

Setup prompts for your key without echoing it. Never paste a key into a shell command or a chat. If your key is already provided securely through the environment, use `setup.py --from-env`. Verify later with `setup.py --check` (one small live API request). Catalogue browsing requires no key. The installer does not read or copy environment credentials.

For a local checkout, run `python3 install.py`, validate with `omarchy plugin validate ~/.config/omarchy/plugins/io.github.cozidian.jev`, then enable with `omarchy plugin enable io.github.cozidian.jev`. The copy installer leaves credentials and keyboard bindings unchanged. Back up your existing plugin before replacing customized code.

Add JEV to the bar using the Omarchy bar editor, or optionally add this line to `~/.config/hypr/bindings.lua` after backing up the file and checking `hyprctl -j binds` for conflicts:

```lua
o.bind("SUPER + ALT + J", "JEV Launcher", "omarchy-shell shell toggle io.github.cozidian.jev")
```

Then run `hyprctl reload` and `hyprctl configerrors`. The shortcut is optional; the stock plugin installer does not create it. Plugin changes normally reload automatically; `omarchy restart shell` reloads QML if needed.

Disable with `omarchy plugin disable io.github.cozidian.jev`; remove the marked JEV binding from `~/.config/hypr/bindings.lua`, reload, and check configerrors.

## Verification

```sh
python3 -m unittest discover -s tests -v
python3 worker.py --catalogue
python3 tests/live_check.py          # live API, preview only, no actions
python3 tests/desktop_check.py       # graphical night-light test; restores original temperature
printf '%s' '{"text":"my eyes feel tired"}' | python3 worker.py --preview
```

Live routing checks cover representative English/Norwegian requests, catalogue operations, typed arguments and denied operations. They do not prove every phrase or every device works. Desktop execution needs a running Omarchy graphical session and the relevant hardware/application.
