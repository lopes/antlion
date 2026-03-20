# Antlion 🐜

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)

Antlion is an AI-powered adversary engagement tool designed to automatically generate high-fidelity, context-aware decoy files (gibberish/mock data).

Strongly inspired by Cliff Stoll's 1986 story, *The Cuckoo's Egg*, Antlion automates the creation of convincing fake data to buy defenders time, track adversaries, and map their behavior.

By strategically placing these files in your environment, you align with the **MITRE Engage** framework to *Expose* adversary presence, *Affect* their movement, and *Elicit* actionable intelligence. Once an adversary interacts with these files, defenders can trigger alerts, deploy embedded honeytokens, mislead the attacker with fake intelligence, or simply delay their lateral movement.

> [!NOTE]
> Antlion is designed for authorized adversary engagement, defensive research, and authorized penetration testing. Do not use this tool on networks where you do not have explicit permission to deploy deceptive artifacts.


## 🧠 How it Works
Creating convincing decoy files manually is tedious and repetitive. Antlion leverages an AI Agent (powered by Anthropic's Claude) to handle this dynamically:

1. **Context Ingestion:** The agent reads operator-defined parameters: base directory, operation name, target file count, file formats, and the specific narrative context (e.g., mimicked teams, corporate environment, tech stack).
2. **Campaign Planning (Structured Data):** The LLM generates a structured roadmap of the decoys, defining realistic file paths, names, types, and summaries. **Crucially, this step forces a structured JSON output enforced via Pydantic.** This guarantees the LLM's response maps perfectly to our internal data objects, eliminating parsing headaches and hallucinations in the file list. (For encrypted files, passwords are intentionally generated and stored in this summary mapping).
3. **Content Generation:** Antlion iterates through the parsed plan, prompting the LLM to write convincing, context-aligned content for each specific file.
4. **File Assembly:** The tool compiles the generated text into the requested formats (including metadata) and writes them to the target operation directory.

*Note: Operators can easily review the generated directory and manually inject specific honeytokens (like canary tokens or fake AWS keys) into the highest-value decoys.*


## 🛠️ Tech Stack & Dependencies
Antlion is built in Python and relies on the following core libraries:
- **LLM Provider:** `anthropic` (Claude 3.5 Sonnet/Opus for advanced reasoning and contextual writing).
- **Data Validation:** `pydantic` (for defining schemas and strictly enforcing structured outputs during the planning phase).
- **Office Formats:** `python-docx` (Word), `openpyxl` (Excel), `python-pptx` (PowerPoint).
- **PDF Handling:** `reportlab` (PDF generation) and `pypdf` (PDF encryption).
- **Package Management:** `uv` for fast, reproducible dependency resolution.

### Supported File Formats
`PDF`, `Encrypted PDF (EPDF)`, `DOCX`, `XLSX`, `PPTX`, `MD`, `CONF`, `JSON`, `XML`


## 🚀 Installation
Ensure you have [uv](https://github.com/astral-sh/uv) installed on your system.

```sh
# Clone the repository
git clone https://github.com/lopes/antlion
cd antlion

# Sync dependencies using uv
uv sync
```

Set your Anthropic API key in your environment:
```sh
export ANTHROPIC_API_KEY="sk-ant-your-api-key-here"
```


## 💻 Usage
Run Antlion by passing your operational parameters.

```sh
uv run python src/antlion.py \
  --base-dir /tmp \
  --operation op_alpha \
  --num-files 99 \
  --formats pdf,epdf,docx,xlsx,conf \
  --teams it,infra,financial \
  --company "mid-sized fintech in Luxembourg, focusing at lending money to people, <50 employees" \
  --file-content "files present information in IT infra, from stack used (MS-AD, zabbix, Cisco ISE, Jamf), including some credentials and old URLs/IP addresses. financial info in the file server includes financial reports and confidential board decision and tax info."
```

The command above will generate a structured directory at `/tmp/op_alpha` containing subfolders and 99 context-aware files mimicking a mid-sized Luxembourg fintech.


## ⚠️ Known Limitations & Architecture Notes
- **Context Window Constraints:** For massive operations exceeding 100+ files, Antlion automatically batches the campaign planning phase to avoid exceeding Claude's output token limits and to maintain the quality of the generated text.


## 📝 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
