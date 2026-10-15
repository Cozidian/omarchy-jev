# JEV Launcher for Omarchy

Press **Super+Alt+J** or click **JEV** in the bar. Describe what you need and press Enter. Clear matches with a reviewed safe operation run automatically. **Preview only** shows the planned operation without running it. Escape or clicking outside closes the overlay.

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

All subprocess calls use argv arrays, `shell=False`, checked exit status and timeouts. App launchers do not inherit captured output pipes. Read-only results are returned in the overlay; dynamic text is rendered as plain text. Night light reads current and final state so repeated “on” stays on. A timeout or command failure may still mean a partial change: inspect the desktop before retrying.

Thresholds and live examples are not a correctness guarantee. A model mistake can choose a different permitted harmless operation; the local policy bounds possible effects.

## Privacy and credentials

No background HTTP server, history database or transcript logging. Catalogue browsing works locally without the API. Submitted requests and relevant command metadata are sent to `https://api.typesafe.ai/v1/systemone` using `jev-latest`. No screen, clipboard, file contents or shortcut command payloads are sent. Shortcut descriptions and key combinations are included only as catalogue metadata. If active shortcuts cannot be read outside the graphical session, command discovery still works. Remote processing follows your TypeSafe account's terms. Reminders themselves are intentionally stored by Omarchy until they fire or are cleared manually.

The worker reads `TYPESAFE_API_KEY`, otherwise `~/.config/omarchy/jev/api-key`, a regular user-owned file with mode 600. The key is never embedded in QML or committed.

## Install and develop

Use `~/.agents/skills/typesafe-ai/SKILL.md` for JEV work and the Omarchy skill for desktop changes. TypeSafe API documentation: https://docs.typesafe.ai/api. Function-calling and hierarchy patterns: https://docs.typesafe.ai/cookbooks/function_calling and https://docs.typesafe.ai/cookbooks/hierarchical_classification.

From this directory:

```sh
python3 install.py
omarchy plugin validate ~/.config/omarchy/plugins/io.github.cozidian.jev
omarchy-shell shell rescanPlugins
```

For a first install, check Super+Alt+J is free with `hyprctl -j binds`, then enable the plugin with `omarchy plugin enable io.github.cozidian.jev`, run `hyprctl reload`, and check `hyprctl configerrors`. The installer copies user-owned plugin files and backs up replaced files and bindings. It preserves existing credentials and configures a new private key file only when the environment key is available and no key file exists. Packaged Omarchy files are untouched.

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
