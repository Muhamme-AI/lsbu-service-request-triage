import type { TriageResult, TriageRun } from "./types"

function saveBlob(content: BlobPart, filename: string, type: string) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

function csvCell(value: string | number | boolean): string {
  const text = String(value ?? "")
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

const CSV_COLUMNS = [
  "Request ID",
  "Submitted Date",
  "Submitted Date (ISO)",
  "Requester Role",
  "Submitted Type",
  "Rule Category",
  "Confidence",
  "Matched Keywords",
  "Category Mismatch",
  "Valid",
  "Validation Issues",
  "Priority",
  "Channel",
  "Status",
  "Needs Human Review",
  "Review Flags",
  "Acknowledgement Source",
  "Acknowledgement",
]

function csvRow(r: TriageResult): (string | number | boolean)[] {
  return [
    r.request.request_id,
    r.request.submitted_date,
    r.submitted_date_iso ?? "",
    r.request.requester_role,
    r.submitted_type,
    r.category.category,
    r.category.confidence,
    r.category.matched_keywords.join("; "),
    r.category_mismatch ? "Yes" : "No",
    r.is_valid ? "Yes" : "No",
    r.validation_issues.map((i) => i.message).join("; "),
    r.request.priority,
    r.request.channel,
    r.request.status,
    r.needs_human_review ? "Yes" : "No",
    r.review_flags.map((f) => `${f.code}: ${f.reason}`).join("; "),
    r.ack_source,
    r.acknowledgement.trim(),
  ]
}

export function downloadCsv(run: TriageRun) {
  const lines = [CSV_COLUMNS.join(","), ...run.results.map((r) => csvRow(r).map(csvCell).join(","))]
  saveBlob(`\uFEFF${lines.join("\r\n")}\r\n`, "triage_results.csv", "text/csv;charset=utf-8")
}

export function downloadJson(run: TriageRun) {
  const { markdown: _markdown, ...rest } = run
  saveBlob(JSON.stringify(rest, null, 2), "triage_results.json", "application/json")
}

export function downloadMarkdown(run: TriageRun, which: "summary" | "acknowledgements") {
  saveBlob(run.markdown[which], `${which}.md`, "text/markdown;charset=utf-8")
}
