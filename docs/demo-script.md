# Demo notes

About five minutes. The command line needs no key. The page uses Groq only when `.env` is present, and it keeps the template if Groq is not configured.

## Start

```bash
python3 -m triage
.venv/bin/uvicorn api.main:app
```

Open http://127.0.0.1:8000. Build the page first with `cd frontend && npm install && npm run build` if `frontend/dist` is missing.

I keep [`output/summary.md`](../output/summary.md) open as well, so I can show the same result as a file.

## 1. The problem (30 seconds)

A small team gets service requests in a spreadsheet. Someone reads each row, checks it is complete, picks a category, writes an acknowledgement and decides what needs a person. The prototype does that first pass. It does not send anything, and it does not decide the awkward cases.

## 2. The supplied file (2 minutes)

Click **Supplied sample**.

Point at the four numbers: 10 read, 10 valid, 6 need a person, 4 can be acknowledged.

Point at the charts. The categories match the types already in the spreadsheet: two of each. That is the rule check. The "why a person" chart is mostly high priority, plus two overdue rows and one external-access request.

Click **REQ-007**. Walk down the dialog:

- the fields are complete;
- Access & Permissions scored 9, on "controlled access" and "external collaborators";
- the flag is `EXTERNAL_ACCESS`, because granting access outside the organisation needs an information-governance check;
- the acknowledgement quotes REQ-007, the date, the channel and "3 working days".

Click **Draft with AI**. With Groq configured, the acknowledgement is rewritten and the note names the model. If the key is missing, or Groq fails, the template stays. That is the point I want to make: the draft is never lost. Azure OpenAI and OpenAI are only called when their keys are set and Groq did not return a usable reply.

## 3. A file with problems (90 seconds)

Close the dialog. Click **Edge cases**.

Point at 7 incomplete and 14 needing a person. Scroll to:

- REQ-102, empty summary, Uncategorised;
- REQ-104, a future date, and a low-confidence category because "connect" and "approval" pull in different directions;
- REQ-107, the example email address and the word password, flagged and not eligible for the AI step;
- REQ-108 twice, duplicate id, and the rules saying Process Automation where the row said Content & Guidance;
- REQ-112, the one row that is ready to send: the type was blank and the rules filled it in, recorded as information rather than a warning.

## 4. The rules are data (45 seconds)

Open the **Rules** tab. The keywords are the contents of `config/rules.json`. A colleague can add a phrase without a code change. Mention that the same decisions are written up as a Power Automate flow in `docs/power-automate-flow-design.md`, for the tools the team already has.

## 5. If they ask to see it as files

```bash
python3 -m triage
```

Open `output/summary.md` and `output/acknowledgements.md`. Same numbers as the screen.

## If I am asked

**Why rules, not a model, for the category?** I need to explain the result, and the same file has to produce the same output next month. The model only rewrites the acknowledgement, and only when I turn it on.

**What did I check?** A future date was skewing the overdue check. A tie in the categoriser was silent. Two tests expected the wrong thing. The model path is tested with a fake HTTP call, so the tests need no key and send no data. Detail is in [`ai-review.md`](ai-review.md).

**What would I not automate?** Anything flagged. Personal data, a disability mention, external access, and a category I am not confident about. The acknowledgement for those is a draft for a person.

**How would this go to production?** One implementation of the rules, a shared mailbox, a Teams channel for the review queue, a managed identity instead of an API key, and an information-governance review of the word list before any model sees a real request.
