# What the assistant drafted, and what I checked or changed

I used a freely available AI assistant for a first draft of the acknowledgement wording, the keyword lists and parts of the test suite. I then ran the prototype and changed anything that did not match the behaviour I wanted. The brief allows Copilot or another assistant, and asks for this note.

## What I kept from the draft

- A standard-library engine in `triage/` that loads a CSV, validates it, categorises it, writes an acknowledgement, raises review flags and writes the output files.
- Rules and templates in `config/`, so the wording can change without a code change.
- An optional model step for the acknowledgement only, with the template kept whenever the model is off, misconfigured or rejected.
- A small HTTP API and a React page for the demo.
- Pytest, GitHub Actions, a second synthetic file, and the Power Automate design.

The ten-row file supplied with the test is unchanged. I added `data/requests_edge_cases.csv` myself so I had something to break the checks on purpose.

## What I changed after running it

1. **A future date was being treated as the clock.** The first run of the edge-case file assessed the batch as of 1 December 2026, because that file contains a planted future date and the code was taking the latest parseable date. Almost every older row then looked overdue. `determine_as_of` now ignores dates after today. The same file is assessed as of 8 October 2026, and REQ-104 is flagged as an invalid date.

2. **A tie had no explanation.** "Connect the purchase order form to the finance approval workflow" scored the same for System Integration and Process Automation, and the winner was whichever category came first in the file. A tie is now broken by the opening verb, marked low confidence, and still sent to a person. Covered by `test_tie_is_broken_by_opening_verb_and_marked_low_confidence`.

3. **The acknowledgement read badly.** The first template said "a Access & Permissions request" and ran the category note into the closing line. It now says "logged as Access & Permissions" and leaves a blank line before "Please quote".

4. **Two tests described the wrong behaviour.** One expected a single blank row to be skipped; a line of empty cells plus an empty line is two blank records, and both are skipped. Another used status New on 1 October and then expected no review, which the overdue rule correctly rejected. I changed the fixture to status Assigned on 7 October so that test checks case-normalisation. The overdue rule kept its own test.

5. **The model step does not call a real service in the tests.** A fake HTTP handler stands in. A normal reply replaces the template and must still quote the reference. A network error, or a reply with the wrong reference, keeps the template. Rows flagged for personal data or sensitive content are not included in the outgoing body. `test_personal_or_sensitive_requests_are_never_sent_to_the_model` asserts the example email address and the word "disability" never appear there.

6. **Groq is the free model I demo, not the categoriser.** Categories stay on the keyword rules, because I can explain every score. Groq rewrites the acknowledgement only. Azure OpenAI and OpenAI are in the same chain and are called only if Groq fails and those keys are set. The template is the last fallback. I would not enable any of them on a real mailbox until information governance had reviewed the word list.

7. **I clicked through the page, not only the tests.** The supplied sample shows 10 valid, 6 needing a person and 4 ready to send. REQ-007 shows the external-access flag, the keyword scores and the acknowledgement. The edge-case file shows 15 rows, 7 incomplete, 14 needing a person and 1 ready to send (REQ-112). Screenshots are in [`screenshots/`](screenshots/).

8. **The review assistant started with gaps the evals found.** The first version indexed the config as one long keyword list, which outranked the written guidance on nearly every question. One chunk per rule fixed it. Stop words ("how", "for a") were carrying matches, so a question about booking a sports hall returned the dashboard note; removing them and raising the relevance floor made off-topic questions return nothing. Redaction replaced the word "password" but left the secret after it, and missed a London phone number; both now use the same patterns as the guardrails. "I'll send it now" slipped past a check that only knew "I have sent". Each of those is now an eval case.

9. **The suite after those changes:** 107 passed on Python 3.14.3, plus 27 guardrail and 11 retrieval evals. The same suite is green on GitHub Actions for Python 3.12, Python 3.14 and the frontend build. See [`test-evidence.md`](test-evidence.md).

## What I would say in the interview

High priority always goes to a person. That is deliberate. Keyword rules will be wrong sometimes, and the mismatch flag is how a person finds those cases. I would not send a live request to Groq, Azure OpenAI or OpenAI until the personal-data check had been agreed with information governance.
