import { ArrowRight, Bot, FileCheck2, FileOutput, ListChecks, MailCheck, ShieldCheck, Tags } from "lucide-react"

import { REPO_URL } from "@/components/Header"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

const STEPS = [
  { icon: FileCheck2, title: "Read the CSV", text: "Headers are matched loosely, the UTF-8 byte-order mark in the supplied file is handled, blank rows are skipped and missing columns become validation issues instead of crashes." },
  { icon: ListChecks, title: "Check required information", text: "Request ID, date (UK format, not in the future), requester role, summary length, priority, channel and status are checked against the allowed values." },
  { icon: Tags, title: "Categorise with simple rules", text: "Weighted keyword rules score each category; the opening verb gets a bonus; ties and weak matches are marked low confidence and the rule result is compared with the submitted type." },
  { icon: MailCheck, title: "Draft an acknowledgement", text: "A template per category with a response target by priority. Optionally rewritten by Groq, the free model. Azure OpenAI and OpenAI are the fallback if Groq fails, and the template is used if every model fails." },
  { icon: ShieldCheck, title: "Flag for human review", text: "Missing information, personal or sensitive data, credentials, duplicates, uncategorised or mismatched requests, external access, high priority and overdue items - each with a plain-English reason." },
  { icon: FileOutput, title: "Write the outputs", text: "triage_results.csv, triage_results.json, summary.md and acknowledgements.md - the same files the command line produces are downloadable here." },
]

const DOCS = [
  { label: "README - how to run everything", path: "README.md" },
  { label: "Submission checklist", path: "SUBMISSION.md" },
  { label: "Prompts used with the AI assistant", path: "docs/prompts.md" },
  { label: "What the AI generated and what was checked or changed", path: "docs/ai-review.md" },
  { label: "Test evidence", path: "docs/test-evidence.md" },
  { label: "Errors, limitations and security considerations", path: "docs/limitations-and-security.md" },
  { label: "Power Automate flow design", path: "docs/power-automate-flow-design.md" },
]

export function AboutView() {
  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">What this prototype does</CardTitle>
          <CardDescription>
            A small team receives service requests in a spreadsheet and someone reviews each one by hand. This prototype does the routine part and leaves the judgement calls to people.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {STEPS.map((step, index) => (
            <div key={step.title} className="grid gap-2 rounded-lg border p-4">
              <div className="flex items-center gap-2">
                <span className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-xs font-semibold text-primary">{index + 1}</span>
                <step.icon className="size-4 text-muted-foreground" />
                <h3 className="text-sm font-medium">{step.title}</h3>
              </div>
              <p className="text-sm text-muted-foreground">{step.text}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Bot className="size-4 text-primary" /> Responsible use of AI
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm text-muted-foreground">
            <p>The core engine is deterministic: the same CSV always gives the same result, and every decision shows its rule and its reason.</p>
            <p>The AI step is optional and off by default. When enabled, the model only receives a small set of facts, the request summary is treated as untrusted text, and replies are checked for length, format and the reference number before use.</p>
            <p>Requests that appear to contain personal or sensitive data are never sent to a model. All data in this repository is synthetic.</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Documentation</CardTitle>
            <CardDescription>Everything the assessment asks for lives in the repository.</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="grid gap-1.5">
              {DOCS.map((doc) => (
                <li key={doc.path}>
                  <a href={`${REPO_URL}/blob/main/${doc.path}`} target="_blank" rel="noreferrer" className="group inline-flex items-center gap-1.5 text-sm text-primary hover:underline">
                    {doc.label}
                    <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
                  </a>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
