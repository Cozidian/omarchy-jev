# Security policy and release review

Report vulnerabilities privately through GitHub Security Advisories for this repository. Do not post keys, personal requests or desktop logs in public issues. If a key was exposed, revoke it with TypeSafe and configure a replacement.

## Boundary

JEV chooses among catalogue identifiers and closed argument choices. Local code owns executable names, argv construction, bounds, intent checks and the default-deny policy. Newly discovered commands, privileged commands, destructive operations, package installation, network changes and arbitrary shell payloads remain suggestion-only. Shortcut discovery excludes dispatcher payloads and never simulates a shortcut. Preview never calls the executor.

The model can still misunderstand a request and choose an allowed operation. Confidence thresholds are not authorization or a guarantee of correctness. Omarchy executables and other plugins run as your desktop user. This plugin does not sandbox that account or protect against malicious same-user software, a compromised Python/runtime, system binaries or API service. Review plugins before installation.

Submitted text and relevant command/shortcut descriptions go to TypeSafe over verified HTTPS. Local browsing is offline. There is no background activity collection, browser-history access or conversation store. Reminder text is intentionally stored by Omarchy. Do not put secrets in requests or shortcut descriptions. Provider retention and account policy are outside this code review.

## Version 1.3.0 review

Code review and offline regression tests cover:

- Redirect authorization forwarding: all redirects refused; a fixed HTTPS endpoint; bounded response reads; no HTTP response bodies in error messages.
- Credential handling: hidden terminal entry, validation before network use, private file precedence, ownership/type/link checks, nonblocking FIFO rejection, fd-based directory traversal without symlinks, atomic private replacement after connection validation, no credential backups or raw exception output.
- Installation: no implicit key import or binding edits, refusal of symlink/nonregular/multiply-linked destinations, standard Omarchy plugin-add compatibility.
- Execution policy: argv arrays without shell evaluation, explicit operation schemas, local numeric/source checks, privileged/mixed requests denied, no model-supplied command arguments. Subprocesses do not inherit the TypeSafe key environment variable.
- UI: plain text results, per-request identifiers to ignore outdated results, 60-second request deadline. Cancelling a worker does not undo a started action; inspect desktop state before retrying.

Release verification includes offline unit tests, live API preview checks, graphical plugin checks and a secret scan of Git history and release source. Live checks use the local private key without printing it. Tests use explicitly synthetic tokens. A clean secret scan reduces risk; it cannot prove an arbitrary unknown string is not a credential. This is a focused maintainer review, not an independent penetration test.
