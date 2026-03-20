# Antlion — Technical Design Document

This document captures the agreed design decisions for Antlion v1. It serves as the single source of truth for implementation.


## Workflow

```
CLI validation → Context ingestion → Campaign planning (batched, Pydantic-enforced JSON)
→ Content generation per file (sequential) → File assembly to disk
```


## CLI Interface

```
uv run python src/antlion.py \
  --base-dir /tmp \
  --operation op_alpha \
  --num-files 99 \
  --formats pdf,epdf,docx,xlsx,pptx,md,conf,json,xml \
  --teams it,infra,financial \
  --company "mid-sized fintech in Luxembourg..." \
  --file-content "files present information in IT infra..." \
  [--model claude-sonnet-4-20250514] \
  [--passwords foobar,Checkbox1] \
  [--resume] \
  [--dry-run]
```

### Parameters

| Parameter        | Required | Validation                                                  | Default                     |
|------------------|----------|-------------------------------------------------------------|-----------------------------|
| `--base-dir`     | Yes      | Must be an existing, writable directory                     | —                           |
| `--operation`    | Yes      | Regex: `^[a-zA-Z0-9][a-zA-Z0-9._-]{0,254}$` (filesystem-safe) | —                       |
| `--num-files`    | Yes      | Integer, 1–`MAX_FILES` (200)                                | —                           |
| `--formats`      | Yes      | Comma-separated; each must be in supported set              | —                           |
| `--teams`        | Yes      | Comma-separated; each team name max 64 chars                | —                           |
| `--company`      | Yes      | Non-empty string, max 256 chars                             | —                           |
| `--file-content` | Yes      | Non-empty string, max 1024 chars                            | —                           |
| `--model`        | No       | Valid Anthropic model identifier                            | `claude-sonnet-4-20250514`  |
| `--passwords`    | No       | Comma-separated list of passwords for EPDF files            | `["abc123", "root"]`        |
| `--resume`       | No       | Flag; enables automatic resume without prompt               | `false`                     |
| `--dry-run`      | No       | Flag; outputs plan to screen, writes nothing to disk        | `false`                     |

### Supported Formats

`pdf`, `epdf`, `docx`, `xlsx`, `pptx`, `md`, `conf`, `json`, `xml`

### Validation Rules

- All parameters are validated before any API call is made.
- If any parameter is invalid, the program exits immediately with an error message and a non-zero exit code.
- If `--formats` contains an unsupported format, the entire run fails (not a partial skip).
- `ANTHROPIC_API_KEY` environment variable must be set; fail immediately at startup if missing.


## Constants

| Name        | Value | Description                          |
|-------------|-------|--------------------------------------|
| `MAX_FILES` | 200   | Upper limit for `--num-files`        |
| `BATCH_SIZE`| 50    | Files per planning batch             |


## Exit Codes

| Code | Meaning                                    |
|------|--------------------------------------------|
| 0    | Success                                    |
| 1    | CLI validation error (bad parameters)      |
| 2    | Environment error (missing API key, etc.)  |
| 3    | API error (network, auth, rate limit)      |
| 4    | Partial completion (some files skipped)    |
| 5    | Planning error (LLM returned invalid plan) |


## Resume Behavior

1. On startup, Antlion checks if `<base-dir>/<operation>/MANIFEST.json` exists.
2. **If manifest exists and `--resume` is passed:** resume automatically — load manifest, skip files that already exist on disk, generate the rest.
3. **If manifest exists and `--resume` is NOT passed:** prompt the user interactively (y/n). If "yes", resume. If "no", delete all files under the operation root (including manifest) and start fresh.
4. **If no manifest exists and `--resume` is passed:** start fresh with a message: `"New operation <name>; starting generation"`.
5. **If no manifest exists and `--resume` is NOT passed:** start fresh (normal behavior).

On resume, Antlion loads the manifest and iterates through its entries. If the file exists on disk, skip it. If not, generate it.


## Dry-Run Behavior

- `--dry-run` outputs the campaign plan to stdout. No files are written to disk.
- `--dry-run` combined with `--resume` on an existing operation: shows only the remaining ungenerated files.
- `--dry-run` on a new operation: runs planning and displays the full plan.


## Manifest (`MANIFEST.json`)

Written to `<base-dir>/<operation>/MANIFEST.json`. Always generated on every run.

```json
{
  "operation": "op_alpha",
  "parameters": {
    "base_dir": "/tmp",
    "num_files": 99,
    "formats": ["pdf", "epdf", "docx", "xlsx", "conf"],
    "teams": ["it", "infra", "financial"],
    "company": "mid-sized fintech in Luxembourg...",
    "file_content": "files present information in IT infra...",
    "model": "claude-sonnet-4-20250514",
    "passwords": ["abc123", "root"]
  },
  "files": [
    {
      "path": "financial/reports/Q3_2025_Revenue.xlsx",
      "format": "xlsx",
      "summary": "Quarterly revenue breakdown by product line for Q3 2025"
    },
    {
      "path": "it/vpn/vpn_gateway.conf",
      "format": "conf",
      "summary": "VPN gateway configuration for the Luxembourg office"
    },
    {
      "path": "infra/policies/access_control.epdf",
      "format": "epdf",
      "summary": "Physical and logical access control policy. Password: abc123"
    }
  ]
}
```

### Manifest Notes

- `path` is relative to the operation root (`<base-dir>/<operation>/`).
- For `epdf` files, the password is included in the `summary` field as: `"<summary>. Password: <password>"`.
- The `parameters` block stores the original CLI parameters for reproducibility and resume validation.


## Duplicate File Path Handling

If the LLM generates duplicate file paths in the plan, Antlion applies macOS-style deduplication:

- First occurrence: `Report.md`
- Second occurrence: `Report (2).md`
- Third occurrence: `Report (3).md`

Deduplication is applied during plan post-processing, before any files are written.


## Campaign Planning

- Uses Anthropic's structured output via tool use with Pydantic model schemas.
- For operations with more than `BATCH_SIZE` (50) files, planning is split into batches of 50 and merged.
- The LLM prompt is formatted with operator context:
  > Consider files created by `{teams}` for the company `{company}` under this context: `{file_content}`.


## Content Generation

- Sequential (one file at a time, no concurrency).
- Progress output to stdout:
  ```
  Generating file 68/99: /tmp/op_alpha/foo/bar/foobar.docx
  ```
- On generation or write failure, log the error and continue to the next file:
  ```
  Generating file 83/99: /tmp/op_alpha/foo/bar/foobar.pptx
      Error generating file: <error details>
  ```
- If any files were skipped, exit with code 4 (partial completion).


## EPDF Password Handling

- A default password list is provided: `["abc123", "root"]`.
- The user can override this list via `--passwords foobar,Checkbox1`.
- During planning, passwords are assigned to EPDF files by cycling through the password list.
- Passwords are recorded in the manifest's summary field for each EPDF entry.


## Format-Specific Generation Notes

| Format | Notes                                                                 |
|--------|-----------------------------------------------------------------------|
| PDF    | Text content with basic formatting                                    |
| EPDF   | Same as PDF, encrypted with a password from the password list         |
| DOCX   | Formatted content: headings, paragraphs, bullet points                |
| XLSX   | Tabular data (rows and columns, not a single text block)              |
| PPTX   | Multiple slides with titles, bullet points, and text                  |
| MD     | Markdown-formatted text                                               |
| CONF   | Generic configuration file format (not tied to specific software)     |
| JSON   | Structured JSON data                                                  |
| XML    | Generic XML data (not tied to specific schema)                        |


## Project Layout

```
antlion/
├── src/
│   ├── antlion.py          # Entrypoint
│   ├── cli.py              # CLI argument parsing and validation
│   ├── planner.py          # Campaign planning (LLM structured output)
│   ├── generator.py        # Content generation orchestration
│   ├── manifest.py         # Manifest read/write
│   ├── models.py           # Pydantic models (CampaignPlan, FileEntry, etc.)
│   ├── write_pdf.py        # PDF writer
│   ├── write_epdf.py       # Encrypted PDF writer
│   ├── write_docx.py       # DOCX writer
│   ├── write_xlsx.py       # XLSX writer
│   ├── write_pptx.py       # PPTX writer
│   ├── write_md.py         # Markdown writer
│   ├── write_conf.py       # CONF writer
│   ├── write_json.py       # JSON writer
│   └── write_xml.py        # XML writer
├── tests/
│   └── ...                 # Tests organized by behavior
├── CLAUDE.md
├── DESIGN.md
├── README.md
└── pyproject.toml
```
