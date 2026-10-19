# Knight Insurance — AI-Assisted Commercial Auto Submission Review

A local Streamlit application for reviewing commercial auto insurance submission packets. It extracts source text, uses an OpenAI model to identify structured underwriting fields and source evidence, evaluates five deterministic checks, and supports auditable human corrections.

## Features

- Upload multiple PDF, TXT, and CSV documents, or paste a broker email.
- Inspect attachment parsing status, extracted text, source locations, and CSV record counts.
- Extract nine business fields with AI, preserving source candidates and evidence.
- Distinguish `KNOWN`, `MISSING`, `CONFLICT`, and `INVALID` fields.
- Run deterministic underwriting checks R1–R5; display `PASS`, `FLAG`, or `UNKNOWN` with supporting explanations.
- Correct extracted values with a mandatory reason, original evidence preservation, and session-only audit history; recalculate rules without another AI call.
- Generate an underwriting summary and editable broker follow-up email. Emails are drafts and are **not** sent automatically.
- Isolate submissions when the packet name, uploaded file contents, or pasted email changes.

## Requirements

- Python 3.11 (tested with Python 3.11.3 on Windows)
- An OpenAI API key with access to the configured model for live extraction
- The dependencies in `requirements.txt`

## Installation — Windows PowerShell

From the project root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` locally and supply your API key. Never commit, upload, or include `.env` in the submission archive.

```dotenv
OPENAI_API_KEY=your_actual_key_here
ENABLE_LIVE_AI=true
```

Launch the application:

```powershell
streamlit run app.py
```

To run without making OpenAI calls, set `ENABLE_LIVE_AI=false`. In this mode, parsing remains available but real-submission AI extraction and underwriting evaluation do not proceed.

## Workflow

1. Enter a packet name, upload documents (`application.pdf`, `broker_email.txt`, `vehicles.csv`, and `loss_runs.pdf` when provided), then click **Process Submission**.
2. Review attachment inventory and extracted source evidence.
3. Review the nine AI-extracted fields and their candidate values, source files, and states.
4. Inspect deterministic R1–R5 results and the overall review status.
5. For missing or conflicting information, enter a **verified corrected value** and a reason in **Phase 6 — Human Overrides**. The application keeps original extraction evidence and records a session-only audit entry.
6. Review the updated underwriting summary and broker email before downloading the draft.
7. Switch to another packet to demonstrate independent processing and cleared review state.

## Architecture

```text
Streamlit UI (app.py)
  -> services/document_parser.py       PDF/TXT/CSV parsing and source locations
  -> services/ai_extractor.py          OpenAI extraction and normalization
  -> models/submission.py              Structured fields, candidates, evidence
  -> services/rules_engine.py          Deterministic underwriting checks
  -> models/rules.py                   Rule result structures
  -> services/human_overrides.py       Corrections and audit records
  -> services/summary_generator.py     Summary and editable broker email
```

The tested live model is **OpenAI `gpt-4.1-mini`**. OpenAI is used for extracting information; the R1–R5 rule outcomes are computed by application code, not chosen by the language model.

## Underwriting rules

| Rule | Purpose |
| --- | --- |
| R1 | Required business name and requested effective date |
| R2 | Declared vehicle count versus validated vehicle schedule count |
| R3 | Operating radius threshold of 150 miles |
| R4 | Hazardous materials declaration |
| R5 | Presence of readable loss runs |

`PASS` means a check is satisfied; `FLAG` means the check identified an issue; `UNKNOWN` means available information is insufficient or unresolved. `READY_FOR_REVIEW` means all five rules passed; it **does not** mean insurance coverage is approved. Otherwise, the application returns `NEEDS_REVIEW`.

## Testing

Run the existing automated suite from the project root:

```powershell
python -m pytest tests/ -v
```

Latest user-run result: **37 tests passed in 3.80 seconds** (Python 3.11.3, pytest 9.1.1). Modules cover extraction, document parsing, overrides, rules, and summary generation.

Manual end-to-end scenarios demonstrated:

| Packet | Expected overall status | Key scenario |
| --- | --- | --- |
| SUB-A | `READY_FOR_REVIEW` | Nine known fields; all five rules pass |
| SUB-B | `NEEDS_REVIEW` | Missing required information and loss runs |
| SUB-C | `NEEDS_REVIEW` | Vehicle mismatch, source conflicts, missing loss runs |

A simulated, explicitly labeled human correction to SUB-C's operating radius changed R3 from `UNKNOWN` to `PASS`, while other unresolved issues remained. Switching from SUB-C to SUB-A in the same browser session showed SUB-A's own fields and no previous override history.

## Configuration and security

- Store `OPENAI_API_KEY` in the local `.env` file; `.env.example` contains placeholders only.
- Set `ENABLE_LIVE_AI=true` only when API usage is intended; API usage may incur charges.
- Keep `.venv`, cache directories, secrets, and local/private submission data out of public repositories and the final ZIP unless the assignment explicitly requires sample files.
- Review source evidence and all AI outputs before underwriting decisions or sending any broker communication.

## Limitations and known constraints

- Human override audit history is held only in the Streamlit browser session, not persisted to a database.
- The application is a local prototype, not a production underwriting system with authentication, durable case management, or access controls.
- LLM extraction can be incomplete or inaccurate; conflicts and missing fields require human verification.
- Broker emails are drafts; no email is automatically sent.
- The 37 automated tests are unit/regression tests; the three packet workflows and session isolation were also manually reviewed in Streamlit.
- Reproducibility of a fresh dependency install has not been independently validated on another machine.

## Development disclosure — complete before submission

- **AI coding assistant(s) used:** [Enter the actual tools used; e.g., ChatGPT, if applicable.]
- **Approximate total development time:** [Enter your actual time spent.]
- **Incomplete features or deviations from the assignment:** [Confirm against the original assignment and list any outstanding items.]

## Demo video checklist (5–10 minutes)

Show upload and parsing, AI fields and source evidence, R1–R5 results, a clearly labeled simulated human correction and recalculation, audit history, summary/email, and switching to a different packet. Do not show API keys or other secrets.
