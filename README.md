# Service Request Triage

A small prototype for the LSBU **AI and Automation Engineer** test.

A team receives service requests in a spreadsheet. Someone reads each row, checks it is complete, decides the category, drafts an acknowledgement and picks out the rows that need a person. This prototype does that routine pass and writes the result to files (and to a small web demo).

The assessment asks for the approach and the reasoning, so the rules, the prompts and the checks are all in this repository rather than hidden in code.

## What it does

For every row in a CSV it:

1. Checks the required information is present and well formed.
2. Assigns a category with keyword rules held in [`config/rules.json`](config/rules.json).
3. Drafts an acknowledgement from [`config/acknowledgements.json`](config/acknowledgements.json).
4. Flags anything a person should look at, with a reason for each flag.
5. Writes `triage_results.csv`, `triage_results.json`, `summary.md` and `acknowledgements.md`.

An optional second step can ask Groq, the free model, to rewrite the acknowledgement. Azure OpenAI and OpenAI stay in the code as the fallback and are called only if Groq fails and those keys are set. The template is used if every provider fails. The step is **off** until `TRIAGE_AI_PROVIDER` is set. Requests that look like they contain personal or sensitive data are never sent to a model.

## Quick start (no installs)

The engine uses the Python standard library only. Python 3.11 or newer.

```bash
python3 -m triage
```

That reads [`data/requests.csv`](data/requests.csv) (the ten synthetic rows supplied with the test) and writes the four files into [`output/`](output/).

```bash
python3 -m triage --input data/requests_edge_cases.csv --output /tmp/triage-edge
python3 -m triage --help
```

`--as-of 2026-10-08` fixes the date used for "future date" and "overdue" checks. With no `--as-of`, the prototype uses the latest valid submission date in the file, so the same CSV always produces the same result.

## Tests

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

The test suite covers loading, validation, categorisation, acknowledgements, review flags, both CSV files end to end, the Groq-to-Azure fallback (no network, no API key) and the HTTP API. `python -m triage.evals` scores the AI guardrails separately.

## Web demo

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
.venv/bin/uvicorn api.main:app
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Load the supplied sample or the edge-case file, or drop in your own CSV. Click a row for the full decision: validation, matched keywords, scores, flags and the acknowledgement.

For UI development, run the API and Vite separately. Vite proxies `/api` to port 8000.

```bash
.venv/bin/uvicorn api.main:app --reload
cd frontend && npm run dev
```

## Deploy on Vercel

[`vercel.json`](vercel.json) is one Vercel project with two services. The page is public at `/`. The API is public at `/api`, which is the path the page already calls. In the Vercel project, set `TRIAGE_AI_PROVIDER` to `groq` and set `GROQ_API_KEY` if acknowledgements should be rewritten by the model. With those unset, the page still runs and uses the templates.

## Optional AI acknowledgements

Copy [`.env.example`](.env.example) to `.env`, set `TRIAGE_AI_PROVIDER=groq` and add a `GROQ_API_KEY` from [console.groq.com](https://console.groq.com/keys). To show the paid fallback in a demo, also fill in `AZURE_OPENAI_API_KEY` or `OPENAI_API_KEY`. `.env` is git-ignored. Setting `TRIAGE_AI_PROVIDER` to `azure` or `openai` uses that provider on its own.

```bash
python3 -m triage --ai
```

The web demo has the same switch, and each request has a "Draft with AI" button. With no `.env` the button explains that AI is not configured and keeps the template. See [`docs/limitations-and-security.md`](docs/limitations-and-security.md) for the guardrails.

## Layout

| Path | What it is |
| --- | --- |
| `triage/` | The engine: load, validate, categorise, acknowledge, review, report, CLI |
| `config/` | Rules and acknowledgement templates, editable without changing code |
| `data/requests.csv` | The ten synthetic requests supplied with the test |
| `data/requests_edge_cases.csv` | Fifteen synthetic rows with deliberate defects |
| `output/` | The result of running the engine on the supplied file |
| `api/` | FastAPI wrapper used by the demo |
| `frontend/` | React, TypeScript and Tailwind demo |
| `tests/` | pytest |
| `docs/` | Prompts, test evidence, AI review, security, Power Automate design, demo script |
| `.github/workflows/ci.yml` | Tests, a fresh triage run, and the frontend build |

## Evidence for the test

[`SUBMISSION.md`](SUBMISSION.md) maps each item the brief asks for to a file in this repository.

## Data

Every row in this repository is synthetic. Do not put real staff, student or university data through the prototype, and do not enable the AI step on a file that might contain personal data you have not already checked. The review rules are a heuristic, not a guarantee.
