# Testing Plan: `aftr refs` Command

## Overview

Three layers of tests, fastest to slowest:

1. **Unit** — `refs.py` core logic, all branches mocked
2. **CLI** — `refs_cmd.py` commands via `CliRunner`, git mocked
3. **Integration** — full sync against a real local bare git repo (no network)

Test file location: `packages/cli/tests/test_refs.py`

---

## Layer 1 — Unit Tests (`aftr.refs`)

### Config I/O

| Test | Setup | Assert |
|---|---|---|
| `test_load_refs_config_empty` | No `.aftr/refs.toml` | Returns `[]` |
| `test_save_then_load_refs_config` | Write 2 sources, reload | All fields round-trip correctly |
| `test_load_refs_config_optional_local_dir` | TOML without `local_dir` | Defaults to `name` |

### State I/O

| Test | Setup | Assert |
|---|---|---|
| `test_load_refs_state_missing` | No `.aftr/.state.json` | Returns `{"sources": {}}` |
| `test_load_refs_state_corrupt_json` | Write invalid JSON | Returns `{"sources": {}}` (no crash) |
| `test_save_then_load_refs_state` | Save state, reload | SHA and timestamp preserved |

### `ensure_gitignore`

| Test | Setup | Assert |
|---|---|---|
| `test_ensure_gitignore_creates_file` | No `.gitignore` | Creates file containing `.aftr/.state.json` |
| `test_ensure_gitignore_appends` | Existing `.gitignore` without the entry | Entry appended |
| `test_ensure_gitignore_idempotent` | Entry already present | File unchanged (no duplicate) |
| `test_ensure_gitignore_preserves_existing_content` | `.gitignore` has other entries | Other entries untouched |

### `get_remote_commit`

Mock `subprocess.run` throughout.

| Test | Mock returns | Assert |
|---|---|---|
| `test_get_remote_commit_success` | `returncode=0`, stdout `"abc123\trefs/heads/main\n"` | Returns `"abc123"` |
| `test_get_remote_commit_nonzero` | `returncode=1` | Returns `None` |
| `test_get_remote_commit_empty_stdout` | `returncode=0`, stdout `""` | Returns `None` |
| `test_get_remote_commit_git_not_found` | `shutil.which("git")` returns `None` | Returns `None` |
| `test_get_remote_commit_timeout` | Raises `TimeoutExpired` | Returns `None` |

### `sync_source`

Mock `subprocess.run` and filesystem copying.

| Test | Setup | Assert |
|---|---|---|
| `test_sync_already_up_to_date` | State SHA == remote SHA | Returns `SyncResult(status="up_to_date")`, no clone called |
| `test_sync_force_bypasses_up_to_date` | State SHA == remote SHA, `force=True` | Proceeds with clone |
| `test_sync_updated` | Remote SHA differs; clone writes files to temp | Returns `SyncResult(status="updated")`, files copied to `.aftr/<local_dir>/`, state updated |
| `test_sync_overwrites_existing_files` | Destination dir already exists | Old dir removed, new files written |
| `test_sync_git_not_available` | `shutil.which` returns `None` | Returns `SyncResult(status="error")` with PATH hint |
| `test_sync_ls_remote_fails` | `ls-remote` returns non-zero | Returns `SyncResult(status="error")` with stderr |
| `test_sync_clone_fails` | Clone returns non-zero | Returns `SyncResult(status="error")` with stderr |
| `test_sync_path_not_in_repo` | Clone succeeds but `source.path` dir missing | Returns `SyncResult(status="error")` |
| `test_sync_cleanup_on_error` | Clone raises `TimeoutExpired` | Temp dir removed; returns `SyncResult(status="error")` |

---

## Layer 2 — CLI Tests (`aftr refs` commands via `CliRunner`)

All tests use `typer.testing.CliRunner` with `mix_stderr=False` and `pytest`'s `tmp_path`.
Git subprocess calls are mocked at `aftr.refs.subprocess.run`.

### `aftr refs list`

| Test | Setup | Assert |
|---|---|---|
| `test_list_no_sources` | Empty project dir | Exit 0; "No sources registered" in output |
| `test_list_with_sources` | Pre-populated `refs.toml` with 2 sources | Exit 0; both names appear in output |
| `test_list_shows_last_synced` | Sources + state with `synced_at` | Exit 0; timestamp visible in output |

### `aftr refs add`

| Test | Setup | Assert |
|---|---|---|
| `test_add_creates_refs_toml` | Clean dir, all flags provided | Exit 0; `.aftr/refs.toml` created with correct fields |
| `test_add_updates_gitignore` | No `.gitignore` | `.gitignore` contains `.aftr/.state.json` |
| `test_add_defaults_local_dir_to_name` | No `--local-dir` | `local_dir == name` in saved config |
| `test_add_custom_local_dir` | `--local-dir custom` | `local_dir == "custom"` in saved config |
| `test_add_duplicate_name_errors` | Source with same name already exists | Exit 1; error message contains name |
| `test_add_second_source_appends` | One source exists, add another | Both present in `refs.toml` |

### `aftr refs sync`

Mock `aftr.refs.subprocess.run`.

| Test | Setup | Assert |
|---|---|---|
| `test_sync_no_sources` | Empty `refs.toml` | Exit 0; "No sources registered" |
| `test_sync_unknown_name` | Source "a" exists, sync "b" | Exit 1 |
| `test_sync_all_up_to_date` | 2 sources; both SHAs match state | Exit 0; "Already up to date" for each |
| `test_sync_all_one_updated` | 2 sources; one SHA differs | Exit 0; "Updated" for changed source |
| `test_sync_named_source` | 2 sources; sync only one by name | Only named source synced |
| `test_sync_error_exits_nonzero` | `ls-remote` fails for one source | Exit 1; error message in output |
| `test_sync_force_flag` | Source up-to-date; `--force` | Clone triggered despite matching SHA |

### `aftr refs remove`

| Test | Input | Assert |
|---|---|---|
| `test_remove_unknown_name` | Name not in config | Exit 1 |
| `test_remove_confirmed` | Existing source; confirm "y" via `input` | Exit 0; source absent from `refs.toml` |
| `test_remove_aborted` | Confirm "n" | Exit 0; source still in `refs.toml` |
| `test_remove_cleans_state` | Source has state entry | State entry removed from `.state.json` |
| `test_remove_delete_files` | `--delete-files`; local dir exists | Local dir removed from filesystem |
| `test_remove_delete_files_missing_dir` | `--delete-files`; no local dir | Exit 0; no error (graceful) |

---

## Layer 3 — Integration Test (real git, no network)

Use a pytest fixture that builds a local bare repository, then run a real `aftr refs sync`.

### Fixture: `local_bare_repo(tmp_path)`

```
tmp_path/
  remote/       ← bare git repo
  work/         ← temporary work tree to seed the bare repo
    guides/
      python.md
      sql.md
```

Steps:
1. `git init --bare tmp_path/remote`
2. `git clone tmp_path/remote tmp_path/work`
3. Create `work/guides/python.md` and `work/guides/sql.md`
4. `git -C work add . && git commit -m "init" && git push`

### Tests using the fixture

| Test | Assert |
|---|---|
| `test_integration_sync_copies_files` | After sync, `.aftr/guides/python.md` and `.aftr/guides/sql.md` exist in project dir |
| `test_integration_state_written` | `.aftr/.state.json` contains correct SHA and `synced_at` |
| `test_integration_sync_twice_is_up_to_date` | Second sync prints "Already up to date", no re-clone |
| `test_integration_sync_after_remote_update` | Push new commit to bare repo; re-sync updates file |
| `test_integration_gitignore_created` | `.gitignore` contains `.aftr/.state.json` after add+sync |

---

## Fixtures and Helpers

```python
# conftest.py additions

@pytest.fixture
def project_dir(tmp_path):
    """A clean project directory (simulates a user's repo root)."""
    return tmp_path

@pytest.fixture
def project_with_source(project_dir):
    """A project dir with one source already registered."""
    sources = [RefsSource(name="guides", url="https://example.com/repo",
                          path="docs/guides", branch="main")]
    save_refs_config(project_dir, sources)
    return project_dir

@pytest.fixture
def local_bare_repo(tmp_path):
    """A real local bare git repo seeded with markdown files."""
    ...  # see Layer 3 fixture above
```

---

## Running the Tests

```bash
# All refs tests
uv run pytest tests/test_refs.py -v

# Unit only (fast)
uv run pytest tests/test_refs.py -v -k "not integration"

# Integration only
uv run pytest tests/test_refs.py -v -k "integration"
```

Mark integration tests with `@pytest.mark.integration` and add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = ["integration: requires git binary and filesystem"]
```
