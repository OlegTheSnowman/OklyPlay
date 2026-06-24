# Custom Rules

- **Changelog Guidelines**: Writing changelogs is necessary only when the changelog matters for the consumer. Backend changes do not require changelog entries, but new features must be documented.

## Git Commit Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/) for all commits. Every commit message must follow this format:

```
<type>(<scope>): <short description>

<optional body>
```

### Types
| Type | When to use |
|------|-------------|
| `feat` | A new feature or user-facing capability |
| `fix` | A bug fix |
| `refactor` | Code restructuring with no behavior change |
| `chore` | Tooling, config, dependencies, build scripts |
| `docs` | Documentation only changes |
| `style` | Formatting, whitespace, naming (no logic change) |
| `test` | Adding or updating tests |
| `perf` | Performance improvements |

### Scopes
Use the module name as the scope, e.g.:
- `feat(audio_engine): add fade-in/fade-out support`
- `fix(project_manager): handle missing sounds directory`
- `chore(deps): add soundfile dependency`
- `feat(ui_main): wire up Ctrl+1..9 bus switching`
- `docs(roadmap): update crossfade specification`

### Commit Granularity
- **Commit after completing each logical unit of work** — typically after finishing a file or a coherent feature within a file.
- **Do NOT batch everything into one giant commit.**
- **Do NOT make empty or WIP commits.**
- Each commit should leave the project in a working state (or at least not break previously working code).

### Workflow
1. After creating/modifying a file, stage it: `git add <file>`
2. Commit with a conventional message: `git commit -m "feat(scope): description"`
3. If a commit touches multiple files for one feature, stage them all and commit together.

### Examples
```
git commit -m "feat(accessible_speech): add Speech singleton with auto-detect"
git commit -m "feat(audio_engine): implement LoadedSound preloading and Channel mixer"
git commit -m "feat(project_manager): add create, load, save, import, export"
git commit -m "feat(ui_dialogs): add new project and preferences dialogs"
git commit -m "feat(ui_main): implement MainFrame with split panel layout"
git commit -m "feat(soundboard): add entry point and app initialization"
git commit -m "fix(audio_engine): prevent clipping on channel summing"
git commit -m "chore: add .gitignore for __pycache__ and .pyc files"
```
