# Test evidence

The brief asks for evidence of three tests. These three are also in the pytest suite, so `python3 -m pytest -q` repeats them. The full run on 15 October 2026 was **108 passed** on Python 3.14.3, and `python3 -m triage.evals` scored 29/29 guardrail cases and 11/11 retrieval cases. Screenshots of the same behaviour in the demo are in [`screenshots/`](screenshots/).

Commands were run from the repository root with the local virtual environment.

## Test 1 — Happy path on the supplied file

**What it checks.** The ten synthetic rows supplied with the test load, validate, and receive the same category the spreadsheet already has. Six need a person; four can be acknowledged as they are.

**Command.**

```bash
.venv/bin/python -m pytest tests/test_pipeline.py::test_sample_batch_end_to_end tests/test_categoriser.py -q
.venv/bin/python -m triage --input data/requests.csv --as-of 2026-10-08
```

**Result.** Both pytest modules passed. The command line printed:

```text
Read 10 requests from requests.csv (as of 2026-10-08, latest submission date in the batch)
  valid: 10   incomplete/invalid: 0
  needs human review: 6   auto-acknowledged: 4
  by category: Access & Permissions 2, Process Automation 2, Reporting & Analytics 2,
               System Integration 2, Content & Guidance 2
  AI drafting: off (templates only)
  review queue:
    - REQ-001    Medium  Access & Permissions     OVERDUE
    - REQ-002    High    Process Automation       HIGH_PRIORITY
    - REQ-004    High    System Integration       HIGH_PRIORITY, OVERDUE
    - REQ-006    High    Process Automation       HIGH_PRIORITY
    - REQ-007    Medium  Access & Permissions     EXTERNAL_ACCESS
    - REQ-009    High    System Integration       HIGH_PRIORITY
```

The written summary is [`output/summary.md`](../output/summary.md). The same numbers appear in the demo: [`screenshots/01-sample-batch-overview.png`](screenshots/01-sample-batch-overview.png) and [`screenshots/02-sample-results-table.png`](screenshots/02-sample-results-table.png).

**What "pass" means.** All ten rows are valid. The rule category matches the submitted type on every row (zero mismatches). REQ-003, REQ-005, REQ-008 and REQ-010 are the four that can be acknowledged without a person.

## Test 2 — Edge cases: missing and invalid information

**What it checks.** A second synthetic file, [`data/requests_edge_cases.csv`](../data/requests_edge_cases.csv), plants one defect per row. The test asserts the flag each defect should raise.

| Row | What was planted | Flag the test expects |
| --- | --- | --- |
| REQ-101 | Requester role left blank | `MISSING_OR_INVALID_INFO` |
| REQ-102 | Summary left blank | `UNCATEGORISED` |
| REQ-103 | Date 31/02/2026 | `MISSING_OR_INVALID_INFO` |
| REQ-104 | Date in the future | `MISSING_OR_INVALID_INFO` |
| REQ-105 | Priority "Urgent", which is not an allowed value | `MISSING_OR_INVALID_INFO` |
| REQ-106 | "Need help with something please." | `UNCATEGORISED` |
| REQ-107 | An example email address, an 8-digit id and the word password | `POSSIBLE_PERSONAL_DATA`, `CREDENTIALS` |
| REQ-108 | The same request id twice, and a summary that is automation rather than the submitted "Content & Guidance" | `DUPLICATE_ID`, `CATEGORY_MISMATCH` |
| REQ-109 | Access for an external examiner | `EXTERNAL_ACCESS` |
| REQ-110 | Still New, submitted 20 September | `OVERDUE` |
| REQ-111 | Summary is the single word "Dashboard" | `LOW_CONFIDENCE` |
| REQ-112 | Request type left blank, summary is clearly an integration | `CATEGORY_ASSIGNED` (info only, no review) |
| REQ-113 | Mentions a disability | `SENSITIVE_CONTENT` |
| row 16 | Request id left blank | `MISSING_OR_INVALID_INFO` |

**Command.**

```bash
.venv/bin/python -m pytest tests/test_pipeline.py::test_edge_case_batch_flags_every_deliberate_defect -q
.venv/bin/python -m triage --input data/requests_edge_cases.csv --output /tmp/triage-edge --as-of 2026-10-08
```

**Result.** The test passed. The command line printed 15 requests, 8 valid, 7 invalid, 14 needing a person and 1 auto-acknowledged (REQ-112). The same counts are in [`screenshots/05-edge-cases-table.png`](screenshots/05-edge-cases-table.png) and [`screenshots/06-edge-cases-overview.png`](screenshots/06-edge-cases-overview.png).

## Test 3 — AI step unavailable, template used instead

**What it checks.** With the AI step switched on, a failure must not drop the acknowledgement and must not send personal data anywhere.

Three situations:

1. The network call fails. Every row keeps its template, and the note says the template was used.
2. The model replies but quotes the wrong reference number. The reply is rejected.
3. The summary looks like personal data (REQ-107) or sensitive content (REQ-113). Those rows are not included in the outgoing request. The test asserts the example email address and the word "disability" are absent from the body that would have been sent.

The HTTP call is replaced with a fake handler, so this test needs no API key and makes no network call. A fourth check hits the real API endpoint with no `.env` and expects `ack_source: template` plus a note that AI is not configured.

**Command.**

```bash
.venv/bin/python -m pytest \
  tests/test_ai.py::test_network_failure_falls_back_to_template \
  tests/test_ai.py::test_reply_without_reference_is_rejected \
  tests/test_ai.py::test_personal_or_sensitive_requests_are_never_sent_to_the_model \
  tests/test_api.py::test_ai_acknowledgement_falls_back_when_not_configured -q
```

**Result.** All four passed. In the demo, with no `.env`, the "Draft with AI" button on REQ-007 leaves the template in place and shows "AI drafting is not configured (set TRIAGE_AI_PROVIDER in .env); template used". See [`screenshots/04-ai-draft-fallback.png`](screenshots/04-ai-draft-fallback.png).

## Test 4 — The review assistant and its retrieval index

**What it checks.** The AI wizard panel answers from indexed guidance and the loaded batch, refuses bad questions before any model call, and drops unsafe model replies. All of it runs with a fake HTTP handler, so no key and no network.

- Seven kinds of question are refused with a named reason and zero model calls: instruction override, a request for the system prompt or a key, pasted personal data, off-topic, empty, and over-long.
- Seven kinds of model reply are dropped and replaced with the retrieved guidance: a claim to have sent an email ("I have sent" and "I'll send it now"), a claim to have granted access, an email address, an invented request reference, HTML, and an empty reply.
- The batch sent to the model is redacted. The test plants an email address, an ID number and `password is hunter2` in a request summary and asserts none of them appear in the outgoing body.
- Groq failing falls back to Azure OpenAI when that key is set, then to the indexed guidance when nothing answers.
- Retrieval: the right guidance file is the top hit for external access, password resets, reminders, email drafts, dashboards, category mismatch, disability, rule keywords and response targets. An off-topic question returns nothing.

**Command.**

```bash
.venv/bin/python -m pytest tests/test_assistant.py tests/test_rag.py -q
.venv/bin/python -m triage.evals
```

**Result.** 41 passed in the two files. The eval run printed `AI guardrail evals: 29/29 passed` and `Retrieval evals: 11/11 passed`.

## The rest of the suite

The other tests cover date parsing (including 31 February and a future date), allowed priorities and channels, whole-word keyword matching ("rapid" must not match "api"), acknowledgement wording, flag severity order, duplicate ids, and the HTTP API (health, rules, sample, upload, a 400 for a CSV with no summary column, a 422 for a bad date, a 422 for an over-long assistant question).

```text
============================= test session starts ==============================
platform darwin -- Python 3.14.3, pytest-9.1.1
collected 108 items
...
============================= 108 passed in 0.79s ==============================
```

GitHub Actions runs the same suite on Python 3.12 and 3.14, reruns both CSV files, and checks that `output/triage_results.csv` still matches a fresh run. See [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).
