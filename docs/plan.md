# Antlion Implementation Plan

## Context

Antlion is a greenfield project — only a stub `main.py` and empty `pyproject.toml` exist. The goal is to implement the full tool as specified in [DESIGN.md](../DESIGN.md), following strict TDD (RED → GREEN → REFACTOR) and functional programming principles from [CLAUDE.md](../CLAUDE.md).

---

## Phase 0: Project Scaffolding

No tests — establish build tooling so `uv run pytest` runs.

1. Update `pyproject.toml`: add all runtime deps (`anthropic`, `pydantic`, `python-docx`, `openpyxl`, `python-pptx`, `reportlab`, `pypdf`) and dev deps (`pytest`). Configure `src/` as package source.
2. Run `uv sync` to install everything. `uv` manages the lockfile — no `requirements.txt` needed.
3. Create directory structure: `src/`, `tests/`, with `__init__.py` files as needed.
4. Move `main.py` → `src/antlion.py`. Run `uv run pytest` to confirm zero tests collected.

---

## Phase 1: Pydantic Models — `src/models.py`

**Tests:** `tests/test_models.py`

All models are frozen (immutable). This module is the **single source of truth** for all constants, enums, and shared types. Every other module imports from here — no magic strings or numbers elsewhere.

| Increment | RED (test) | GREEN (code) |
|-----------|-----------|--------------|
| 1.1 | `SUPPORTED_FORMATS` is a frozenset of exactly 9 formats | Define constant |
| 1.2 | `MAX_FILES == 200`, `BATCH_SIZE == 50` | Define constants |
| 1.3 | `DEFAULT_MODEL == "claude-sonnet-4-20250514"`, `DEFAULT_PASSWORDS == ("abc123", "root")` | Define constants |
| 1.4 | Exit code constants: `EXIT_SUCCESS == 0`, `EXIT_CLI_ERROR == 1`, `EXIT_ENV_ERROR == 2`, `EXIT_API_ERROR == 3`, `EXIT_PARTIAL == 4`, `EXIT_PLANNING_ERROR == 5` | Define constants |
| 1.5 | `FileEntry(path, format, summary)` — frozen, format validated against `SUPPORTED_FORMATS` | Frozen BaseModel with validator |
| 1.6 | `CampaignPlan(files=[...])` — frozen, accepts list of FileEntry | Frozen BaseModel |
| 1.7 | `OperationParameters(base_dir, num_files, formats, teams, company, file_content, model, passwords)` — frozen, represents the manifest's parameters block (no CLI flags like resume/dry_run) | Frozen BaseModel |
| 1.8 | `Manifest(operation, parameters, files)` — frozen, round-trip JSON serialization | Frozen BaseModel |

---

## Phase 2: CLI Parsing — `src/cli.py`

**Tests:** `tests/test_cli_validation.py`

Pure function: `parse_args(argv) -> CliArgs | CliError`. No side effects. All limits and defaults reference constants from `models.py`.

The return type `CliArgs` includes everything from `OperationParameters` plus the CLI-only flags (`resume`, `dry_run`, `operation`). It is a separate frozen type from `OperationParameters`.

| Increment | Behavior tested |
|-----------|----------------|
| 2.1 | Happy path — all required args parse correctly, defaults from `DEFAULT_MODEL` and `DEFAULT_PASSWORDS` applied |
| 2.2 | Missing required arg → `CliError` |
| 2.3 | `--operation` regex validation (valid and invalid cases) |
| 2.4 | `--num-files` range 1–`MAX_FILES` |
| 2.5 | `--formats` validated against `SUPPORTED_FORMATS` |
| 2.6 | `--teams` max 64 chars per team |
| 2.7 | `--company` max 256, `--file-content` max 1024, both non-empty |
| 2.8 | Optional params: `--model`, `--passwords`, `--resume`, `--dry-run` |
| 2.9 | `--base-dir` must be existing writable directory |

---

## Phase 3: File Writers — `src/write_*.py`

**Tests:** `tests/test_writers.py`

Each writer is a pure function: `write_<fmt>(content, path) -> None`. All create parent dirs.

| Increment | Writer | Verification |
|-----------|--------|-------------|
| 3.1–3.2 | `write_md` | Content matches input; creates nested dirs |
| 3.3 | `write_json` | Valid JSON roundtrip via `json.load` |
| 3.4 | `write_xml` | Content preserved |
| 3.5 | `write_conf` | Content preserved |
| 3.6 | `write_pdf` (reportlab) | File starts with `%PDF` magic bytes |
| 3.7 | `write_epdf` (reportlab + pypdf) | Encrypted; correct password unlocks, no password raises |
| 3.8 | `write_docx` (python-docx) | Opens without error via `Document(path)` |
| 3.9 | `write_xlsx` (openpyxl) | Cell values match parsed CSV input |
| 3.10 | `write_pptx` (python-pptx) | `Presentation(path)` loads, slide count ≥ 1 |
| 3.11 | `get_writer(format)` dispatch | Returns correct callable per format; `ValueError` on unknown |

---

## Phase 4: Manifest — `src/manifest.py`

**Tests:** `tests/test_manifest.py`

| Increment | Behavior |
|-----------|----------|
| 4.1 | `write_manifest(manifest, dir)` creates `MANIFEST.json`, roundtrips |
| 4.2 | `read_manifest(dir)` returns `Manifest` or `None` |
| 4.3 | `manifest_exists(dir)` returns bool |

---

## Phase 5: Plan Post-Processing (pure functions)

**Tests:** `tests/test_plan_processing.py`

| Increment | Function | Behavior |
|-----------|----------|----------|
| 5.1 | `deduplicate_paths` | `Report.md` → `Report.md`, `Report (2).md`, `Report (3).md` |
| 5.2 | `assign_epdf_passwords` | Cycles passwords via `itertools.cycle`, appends to summary |
| 5.3 | `merge_plans` | Concatenates file lists from multiple `CampaignPlan`s |
| 5.4 | `post_process_plan` | Composes merge → dedup → password assignment |

---

## Phase 6: Campaign Planner — `src/planner.py`

**Tests:** `tests/test_planner.py` (API mocked)

| Increment | Behavior |
|-----------|----------|
| 6.1 | `compute_batches(num_files)` → list of `(batch_num, count)` tuples (uses `BATCH_SIZE`) |
| 6.2 | `build_planning_prompt(...)` → formatted string with all context |
| 6.3 | `plan_batch(client, prompt, batch_size)` → `CampaignPlan` (mocked API, Anthropic structured output with Pydantic schema) |
| 6.4 | `plan_campaign(client, params)` → full post-processed plan (mocked, 2 batches) |
| 6.5 | API error → `PlanningError` (maps to exit code 3) |
| 6.6 | Invalid LLM response → `PlanningError` (maps to exit code 5) |

---

## Phase 7: Content Generator — `src/generator.py`

**Tests:** `tests/test_generator.py` (API mocked)

| Increment | Behavior |
|-----------|----------|
| 7.1 | `generate_file_content(client, entry, model)` → content string |
| 7.2 | `write_generated_file(content, entry, op_dir, passwords)` → dispatches to correct writer via `get_writer` |
| 7.3 | `generate_all(client, manifest, op_dir)` → creates all files sequentially |
| 7.4 | Error resilience — failed file is skipped, others still created, failure count returned |
| 7.5 | Resume — existing files skipped, API called only for missing |
| 7.6 | Progress output: `"Generating file N/M: <full_path>"` |

---

## Phase 8: Resume & Dry-Run Logic

**Tests:** `tests/test_resume_and_dryrun.py`

| Increment | Behavior |
|-----------|----------|
| 8.1 | `determine_resume_action(manifest_exists, resume_flag)` → `"resume"` / `"prompt"` / `"fresh_with_message"` / `"fresh"` |
| 8.2 | Dry-run on new operation: plan printed, no files written |
| 8.3 | Dry-run + resume: shows only remaining ungenerated files |

---

## Phase 9: Entrypoint — `src/antlion.py`

**Tests:** `tests/test_entrypoint.py`

This is the **main orchestration loop**. The `run(argv) -> int` function (returns exit code, no `sys.exit` for testability) implements:

```
1. parse_args(argv)              → CliArgs or exit 1
2. check ANTHROPIC_API_KEY       → or exit 2
3. build operation_dir           → base_dir / operation
4. determine_resume_action       → resume / prompt / fresh_with_message / fresh
5. if fresh and dir exists       → delete operation dir
6. if resuming                   → read_manifest(operation_dir)
7. else                          → plan_campaign(client, params)  [batched 50-by-50]
                                 → create operation dir
                                 → write_manifest(manifest, operation_dir)
8. if dry_run                    → print plan to stdout, exit 0
9. generate_all(client, manifest, operation_dir, resume=...)
10. return EXIT_SUCCESS or EXIT_PARTIAL based on failure count
```

Errors from the planner or API are caught and mapped to exit codes 3/5.

| Increment | Behavior tested |
|-----------|----------------|
| 9.1 | Bad CLI args → `EXIT_CLI_ERROR` (1) |
| 9.2 | Missing `ANTHROPIC_API_KEY` → `EXIT_ENV_ERROR` (2) |
| 9.3 | Successful full run (fully mocked) → `EXIT_SUCCESS` (0), files + manifest created |
| 9.4 | Partial completion (one file fails) → `EXIT_PARTIAL` (4) |
| 9.5 | Planning error (invalid LLM response) → `EXIT_PLANNING_ERROR` (5) |
| 9.6 | API error (network/auth) → `EXIT_API_ERROR` (3) |

---

## Phase 10: Integration Smoke Tests

**Tests:** `tests/test_integration.py`

| Increment | Scenario |
|-----------|----------|
| 10.1 | End-to-end with mocked LLM: 5 files, 3 formats → all created + manifest |
| 10.2 | Resume: delete 2 files, re-run with `--resume` → only 2 regenerated |
| 10.3 | Dry-run: no files/dirs created, plan printed to stdout |

---

## Dependency Order

```
Phase 0 → Phase 1 → Phases 2, 3, 4, 5 (independent of each other)
                         ↓
                   Phase 6 (needs 1, 5)
                   Phase 7 (needs 1, 3, 4)
                   Phase 8 (needs 1, 4)
                         ↓
                   Phase 9 (needs all above)
                         ↓
                   Phase 10 (validation)
```

## Verification

After each increment: `uv run pytest` must pass (all green).

Final verification:
- `uv run pytest` — all tests pass
- `uv run python src/antlion.py --help` — shows all parameters
- Manual run with `--dry-run` and a real API key to verify LLM integration
- Manual run generating a few files across all 9 formats

## Critical Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Dependencies managed by `uv` (no requirements.txt) |
| `src/models.py` | Single source of truth: constants (`MAX_FILES`, `BATCH_SIZE`, `DEFAULT_MODEL`, `DEFAULT_PASSWORDS`, exit codes), types (`FileEntry`, `CampaignPlan`, `OperationParameters`, `Manifest`) |
| `src/cli.py` | Pure-function CLI parsing; all limits/defaults imported from `models.py` |
| `src/planner.py` | Anthropic structured output, batching by `BATCH_SIZE`, post-processing |
| `src/generator.py` | Sequential generation loop with resume, error resilience, progress output |
| `src/manifest.py` | Manifest read/write |
| `src/write_*.py` | One writer per format (9 files) |
| `src/antlion.py` | Main orchestration loop: CLI → env check → resume logic → plan → manifest → generate → exit code |
