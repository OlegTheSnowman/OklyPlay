# Token-Efficiency Rules (read before every action)

## Tool priority order — ALWAYS follow this sequence

1. **memory MCP** (`create_entities`, `search_nodes`, `open_nodes`) — check here first for anything already known about the project
2. **code-review-graph MCP** — for all code exploration, impact analysis, review
3. **fetch MCP** — for web content (instead of WebFetch when possible)
4. **Grep/Glob** — only if graph has no answer
5. **Read** — last resort; use `get_minimal_context_tool` or `get_review_context` instead

Never open a file just to orient yourself. Never Grep for something the graph already knows.

---

## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`
- **Minimal context**: `get_minimal_context_tool` — get only the lines you need

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
| ------ | ---------- |
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_minimal_context_tool` | Need only specific lines — most token-efficient Read |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.

---

## MCP Tools: memory

Persistent knowledge graph across sessions. Saves re-deriving project context.

- **Start of session**: call `search_nodes` with project name to recall known entities
- **After learning something non-obvious**: call `create_entities` or `add_observations`
- **Store**: architecture decisions, key patterns, module responsibilities, known bugs, conventions
- **Do NOT store**: things derivable from code (covered by code-review-graph)

---

## MCP Tools: fetch

Use instead of WebFetch when fetching documentation or external URLs. Returns cleaner markdown with fewer tokens.

---

## Context window discipline

- Stay out of the last 20% of the context window for multi-file tasks — start a new session
- Responses must be concise — no trailing summaries, no restating what was just done
- Parallel tool calls whenever operations are independent
- Never re-read a file you just edited — trust the tool result

---

## Agent conventions (from ~/.claude/rules/ecc/common/agents.md)

**Always invoke these agents — no user prompt needed:**

| Trigger | Agent |
|---------|-------|
| After writing or modifying Python code | `python-reviewer` |
| Complex feature / multi-file change | `planner` first |
| Bug fix or new feature | `tdd-guide` |
| Architectural decision | `architect` |
| Build fails | `build-error-resolver` |

**Parallel execution:** launch independent agents in a single message.

**Commit after every completed feature** using conventional commits:
`feat:`, `fix:`, `refactor:`, `test:`, `chore:`, `docs:`
