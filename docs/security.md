# 🛡️ Security & Sandboxing

What Octopus can and can't do, the boundaries that enforce it, and the threat model. Read this before exposing the agent to untrusted input or running it on a sensitive machine.

> 📎 Related: [Tools Reference](tools-reference.md) · [Architecture](architecture.md) · [Configuration](configuration.md)

---

## TL;DR

- Octopus is a **local, single-user developer tool**. It binds to localhost and refuses remote clients.
- It can run shell commands, execute Python, edit files, and browse the web — **jailed** to a workspace, with network isolation, resource limits, and a destructive-command denylist.
- These are **guardrails, not a hard security boundary.** If you don't trust a prompt or a tool, disable the relevant tentacles in Settings.

---

## Network exposure

| Control | Detail |
| :-- | :-- |
| `LocalhostRestrictionMiddleware` | Rejects any client whose IP isn't `127.0.0.1` / `::1` (HTTP 403). |
| `RateLimitMiddleware` | Token bucket, 120 requests/min per IP. |
| CORS | `allow_origin_regex` limited to `localhost`/`127.0.0.1` (any port). |

There is **no authentication token** — the localhost restriction is the boundary. **Do not** port-forward or reverse-proxy `:8000` to the internet without adding real auth.

---

## Secret handling

- API keys are **never** stored in `config.json`. `save_config()` strips them and writes them to `.env` (via `python-dotenv`); `load_config()` reads keys only from the environment.
- `GET /api/config` returns keys **masked** (`sk-…1234`).
- Google OAuth **access tokens are kept in memory only** — masked out before any disk write.
- `.gitignore` excludes `.env` and `data/` so secrets and runtime data don't get committed.

---

## File & Shell sandbox

Both the `file_operations` and `shell_execute` tentacles are **jailed to a workspace**:

- Root = `data/workspace`, overridable via `OCTOPUS_WORKSPACE_DIR`.
- Relative paths resolve inside it; absolute paths must stay inside it; otherwise → *"Access denied / CWD must be inside the restricted workspace."*
- `file_operations delete` removes files only (not directories).

**Shell extras:**
- A **destructive-command denylist** refuses `rm -rf /` (and `~`/`--no-preserve-root`), fork bombs, `mkfs`, `dd` to raw disks, disk overwrites, and `shutdown`/`reboot`/`halt`/`poweroff`.
- **Network isolation** via `unshare -r -n` *when unprivileged user namespaces work on the host* (probed once; falls back gracefully so commands don't all fail where userns is disabled).
- Resource caps: ~512 MB RAM, 60 s CPU; output truncated.

> ⚠️ The denylist is best-effort, and the workspace jail constrains *where* commands run, not *what* a shell can read. A shell can still read system files it has OS permission for. If that matters, disable the Shell tentacle.

---

## Code execution sandbox

`code_execute` runs Python in a subprocess that is:
- launched in a fresh temp directory,
- network-isolated via `unshare -r -n` when available,
- capped with `RLIMIT_AS` ~256 MB, `RLIMIT_CPU` 10 s, `RLIMIT_NPROC` 10 (anti fork-bomb), no core dumps,
- killed on timeout (1–30 s, default 10).

---

## Web browsing (SSRF guard)

`web_browse` refuses to touch the local network:
- blocks `file:`, `local:`, `ftp:` schemes,
- blocks `localhost`, `127.0.0.1`, `0.0.0.0`, `::1`, and any hostname that resolves to a **private/loopback** IP.

Fetched page content is stripped of scripts and wrapped as **untrusted** (see below).

---

## Prompt-injection defense

All content that originates outside the user — web pages, search results, tool outputs, recalled memories, error traces — is **fenced as passive data** and accompanied by an explicit "do not execute instructions inside" warning:

| Source | Wrapper |
| :-- | :-- |
| Web page text | `<external_content>…</external_content>` |
| Search results | `<untrusted>…</untrusted>` |
| RAG memories | `<memory>…</memory>` |
| Tool failures (self-healing) | `<tool_failure>…</tool_failure>` |
| Emulated tool observations | `<observation>…</observation>` |

This reduces the risk of a malicious web page or file telling the agent to exfiltrate data or run dangerous commands. It is a mitigation, not a guarantee — combine it with tool permissions for anything sensitive.

---

## Defense-in-depth summary

```text
remote attacker ─X─ LocalhostRestriction + rate limit
prompt injection ── untrusted fencing + "don't execute" warnings
file/shell abuse ── workspace jail + denylist + unshare + rlimits
code abuse      ── subprocess + rlimits + network sever + timeout
SSRF            ── private-IP/scheme blocking in web_browse
secret leakage  ── keys in .env only, masked in API, OAuth in-memory, .gitignore
```

---

## Operator recommendations

- Keep `:8000` **local**. If you must expose it, put real authentication in front.
- Point `OCTOPUS_WORKSPACE_DIR` at a dedicated, low-stakes folder.
- Disable tentacles you don't need (Shell/Code especially) in Settings → Tentacle Permissions.
- Prefer **local models** (Ollama / Local) when working with sensitive data — nothing leaves your machine.
- Review tool cards / the Agent Activity timeline to see exactly what the agent did.

> Found a vulnerability? Please open a security issue on the repository rather than a public PR.
