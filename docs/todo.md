# Antlion Implementation Todo

## Progress Tracker

- [ ] **Phase 0:** Project scaffolding (pyproject.toml, dirs, uv sync)
- [ ] **Phase 1:** Pydantic models in `src/models.py`
- [ ] **Phase 2:** CLI parsing in `src/cli.py`
- [ ] **Phase 3:** File writers (`src/write_*.py`)
- [ ] **Phase 4:** Manifest read/write in `src/manifest.py`
- [ ] **Phase 5:** Plan post-processing (dedup, passwords, merge)
- [ ] **Phase 6:** Campaign planner in `src/planner.py`
- [ ] **Phase 7:** Content generator in `src/generator.py`
- [ ] **Phase 8:** Resume & dry-run logic
- [ ] **Phase 9:** Entrypoint orchestration in `src/antlion.py`
- [ ] **Phase 10:** Integration smoke tests

## Detailed Increments

### Phase 0: Project Scaffolding
- [ ] 0.1 Update `pyproject.toml` with all deps
- [ ] 0.2 Run `uv sync`
- [ ] 0.3 Create `src/`, `tests/` directories
- [ ] 0.4 Move `main.py` → `src/antlion.py`, confirm `uv run pytest` runs

### Phase 1: Pydantic Models
- [x] 1.1 `SUPPORTED_FORMATS` frozenset
- [x] 1.2 `MAX_FILES`, `BATCH_SIZE` constants
- [x] 1.3 `DEFAULT_MODEL`, `DEFAULT_PASSWORDS` constants
- [x] 1.4 Exit code constants (0–5)
- [x] 1.5 `FileEntry` frozen model with format validator
- [x] 1.6 `CampaignPlan` frozen model
- [x] 1.7 `OperationParameters` frozen model
- [x] 1.8 `Manifest` frozen model with JSON round-trip

### Phase 2: CLI Parsing
- [ ] 2.1 Happy path — all required args, defaults applied
- [ ] 2.2 Missing required arg → `CliError`
- [ ] 2.3 `--operation` regex validation
- [ ] 2.4 `--num-files` range 1–`MAX_FILES`
- [ ] 2.5 `--formats` against `SUPPORTED_FORMATS`
- [ ] 2.6 `--teams` max 64 chars per team
- [ ] 2.7 `--company` max 256, `--file-content` max 1024
- [ ] 2.8 Optional params: `--model`, `--passwords`, `--resume`, `--dry-run`
- [ ] 2.9 `--base-dir` existing writable directory

### Phase 3: File Writers
- [ ] 3.1–3.2 `write_md` + nested dir creation
- [ ] 3.3 `write_json`
- [ ] 3.4 `write_xml`
- [ ] 3.5 `write_conf`
- [ ] 3.6 `write_pdf` (reportlab)
- [ ] 3.7 `write_epdf` (reportlab + pypdf)
- [ ] 3.8 `write_docx` (python-docx)
- [ ] 3.9 `write_xlsx` (openpyxl)
- [ ] 3.10 `write_pptx` (python-pptx)
- [ ] 3.11 `get_writer` dispatch function

### Phase 4: Manifest
- [ ] 4.1 `write_manifest` creates `MANIFEST.json`
- [ ] 4.2 `read_manifest` returns `Manifest` or `None`
- [ ] 4.3 `manifest_exists` returns bool

### Phase 5: Plan Post-Processing
- [ ] 5.1 `deduplicate_paths` — macOS-style `(N)` suffixes
- [ ] 5.2 `assign_epdf_passwords` — cycled from password list
- [ ] 5.3 `merge_plans` — concatenate file lists
- [ ] 5.4 `post_process_plan` — compose merge → dedup → passwords

### Phase 6: Campaign Planner
- [ ] 6.1 `compute_batches` — batch count calculation
- [ ] 6.2 `build_planning_prompt` — formatted prompt string
- [ ] 6.3 `plan_batch` — single batch (mocked API)
- [ ] 6.4 `plan_campaign` — full orchestration (mocked, 2 batches)
- [ ] 6.5 API error handling → `PlanningError`
- [ ] 6.6 Invalid LLM response → `PlanningError`

### Phase 7: Content Generator
- [ ] 7.1 `generate_file_content` — single file content (mocked API)
- [ ] 7.2 `write_generated_file` — dispatch to correct writer
- [ ] 7.3 `generate_all` — sequential loop
- [ ] 7.4 Error resilience — skip failed, continue
- [ ] 7.5 Resume — skip existing files
- [ ] 7.6 Progress output

### Phase 8: Resume & Dry-Run
- [ ] 8.1 `determine_resume_action` pure function
- [ ] 8.2 Dry-run new operation — plan printed, no files
- [ ] 8.3 Dry-run + resume — show remaining only

### Phase 9: Entrypoint
- [ ] 9.1 Bad CLI args → exit 1
- [ ] 9.2 Missing API key → exit 2
- [ ] 9.3 Full run (mocked) → exit 0, files created
- [ ] 9.4 Partial completion → exit 4
- [ ] 9.5 Planning error → exit 5
- [ ] 9.6 API error → exit 3

### Phase 10: Integration
- [ ] 10.1 End-to-end with mocked LLM (5 files, 3 formats)
- [ ] 10.2 Resume integration test
- [ ] 10.3 Dry-run integration test
