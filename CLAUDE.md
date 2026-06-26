# Claude Agent Instructions for OklyPlay

Read `AGENTS.md` (project root) and `src/AGENTS.md` at the start of every session — they are the authoritative source on architecture, constraints, and workflow. The rules below are operational shortcuts layered on top.

---

## Project essentials (from AGENTS.md)

- **Purpose**: Screenreader-accessible soundboard for streamers. Accessibility is the top priority — every UI element must work without a mouse and be announced correctly by NVDA/JAWS.
- **Stack**: wxPython · sounddevice · soundfile · NumPy · accessible_output2 · PyInstaller
- **Thread model**: Real-time audio runs in a sounddevice callback thread. The main thread is wxPython's event loop. `AudioEngine` uses copy-on-write on `_active_channels` — no mutexes.
- **Cleanup timer**: `OnCleanupTimer` fires every 100 ms — removes done channels, updates status bar, advances playlists with track-crossfade logic.
- **Accessibility rules**: call `label_control(control, text)` on every input; use `Speech.speak()` for state changes; never add mouse-only interactions.

---

## Git workflow

**Always use feature branches — never commit directly to `master`.**

```
git checkout -b feat/my-feature   # branch off master
# ... do work, commit ...
git push -u origin feat/my-feature
gh pr create --base master
```

**Commit format** (Conventional Commits, required):
`<type>(<scope>): <description>`

Common types: `feat` `fix` `refactor` `chore` `docs` `style` `test` `perf`
Common scopes: `audio_engine` `project_manager` `ui_main` `ui_dialogs` `soundboard` `changelog`

**Releasing**: bump `src/version.py`, commit as `chore(release): bump version to vX.Y.Z`, tag `vX.Y.Z`, push tag — CI builds and publishes the executable automatically.

---

## Tool priority order

1. **memory MCP** — check at session start for known project context
2. **code-review-graph MCP** — all exploration, impact analysis, review (faster and cheaper than file reads)
3. **fetch MCP** — external docs/URLs
4. **Grep/Glob** — only if graph has no answer
5. **Read** — last resort

Never open a file just to orient yourself. Never Grep for something the graph already knows.

### code-review-graph quick reference

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes |
| `get_review_context` | Need source snippets for review |
| `get_impact_radius` | Blast radius of a change |
| `get_affected_flows` | Which execution paths are impacted |
| `query_graph` | Callers, callees, imports, tests |
| `semantic_search_nodes` | Find functions/classes by name or keyword |
| `get_architecture_overview` | High-level structure |

---

## Agent conventions

**Always invoke — no user prompt needed:**

| Trigger | Agent |
|---------|-------|
| After writing or modifying Python code | `python-reviewer` |
| Complex / multi-file feature | `planner` first |
| New feature or bug fix | `tdd-guide` |
| Architectural decision | `architect` |
| Build fails | `build-error-resolver` |

Run independent agents in parallel in a single message.

---

## Running tests

```
python -m pytest tests/ -v
# Target a specific suite to avoid wx access violations on Windows:
python -m pytest tests/ -k TestAudioEngine
```

---

## Context discipline

- Stay out of the last 20 % of context for multi-file tasks — start a new session
- Parallel tool calls whenever operations are independent
- Never re-read a file you just edited — trust the tool result
- No trailing summaries, no restating what was just done
