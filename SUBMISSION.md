# Submission checklist

This is the pack for the AI and Automation Engineer test. Each line is one thing the brief asks for, and where it is.

| Evidence the brief asks for | Where it is |
| --- | --- |
| The prototype, script, flow or workflow design | Python engine in [`triage/`](triage/), HTTP API in [`api/`](api/), demo UI in [`frontend/`](frontend/), and a Power Automate design in [`docs/power-automate-flow-design.md`](docs/power-automate-flow-design.md) |
| Synthetic input data | [`data/requests.csv`](data/requests.csv) (the file supplied with the test, ten rows) and [`data/requests_edge_cases.csv`](data/requests_edge_cases.csv) (fifteen extra synthetic rows) |
| Synthetic output data | [`output/triage_results.csv`](output/triage_results.csv), [`output/triage_results.json`](output/triage_results.json), [`output/summary.md`](output/summary.md), [`output/acknowledgements.md`](output/acknowledgements.md) |
| The prompts used with the AI assistant | [`docs/prompts.md`](docs/prompts.md) |
| Evidence of three tests | [`docs/test-evidence.md`](docs/test-evidence.md) and the pytest suite in [`tests/`](tests/) |
| What the assistant generated, and what was checked or changed | [`docs/ai-review.md`](docs/ai-review.md) |
| Errors, limitations and security considerations | [`docs/limitations-and-security.md`](docs/limitations-and-security.md) |
| Ready to demo | [`docs/demo-script.md`](docs/demo-script.md). Run `uvicorn api.main:app` and open the site, or run `python3 -m triage` |

## What the prototype covers from the brief

- Reads the ten supplied requests (the brief asks for at least five).
- Checks required information: request id, date, role, summary, priority, channel and status.
- Categorises with simple rules in [`config/rules.json`](config/rules.json). On the supplied file the rule category matches the submitted type for all ten rows.
- Writes a suggested acknowledgement for every row.
- Marks six of the ten for human review (overdue, high priority, or access for an external party) and says why.
- Writes the output files above.

## How to run it in front of someone

```bash
python3 -m triage
.venv/bin/uvicorn api.main:app
```

No API key is required. The AI acknowledgement step is documented and tested, and it stays off unless `.env` is filled in.

## What was deliberately not done

No real personal, staff, student or university data is in the repository or in the screenshots. No paid software is required. Power Automate is designed in [`docs/power-automate-flow-design.md`](docs/power-automate-flow-design.md) rather than executed, because the brief says a documented workflow is acceptable where a licence is not available.
