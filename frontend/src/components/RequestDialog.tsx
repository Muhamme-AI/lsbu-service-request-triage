import { useEffect, useState } from "react"
import { AlertCircle, Check, Copy, Loader2, ShieldCheck, Sparkles } from "lucide-react"

import { ConfidenceDot, PriorityBadge, SeverityBadge, SourceBadge } from "@/components/badges"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { api, ApiError } from "@/lib/api"
import type { Health, TriageResult } from "@/lib/types"
import { cn, formatIsoDate } from "@/lib/utils"

interface RequestDialogProps {
  result: TriageResult | null
  health: Health | null
  asOf: string
  onClose: () => void
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h3>
      {children}
    </section>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-0.5">
      <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm">{value || <span className="text-muted-foreground italic">blank</span>}</dd>
    </div>
  )
}

export function RequestDialog({ result, health, asOf, onClose }: RequestDialogProps) {
  const [ack, setAck] = useState<{ text: string; source: "template" | "ai"; note: string | null } | null>(null)
  const [drafting, setDrafting] = useState(false)
  const [draftError, setDraftError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (result) {
      setAck({ text: result.acknowledgement, source: result.ack_source, note: result.ai_note })
      setDraftError(null)
      setCopied(false)
    }
  }, [result])

  if (!result || !ack) return null

  const req = result.request
  const maxScore = Math.max(1, ...Object.values(result.category.scores))
  const aiBlocked = result.review_flags.some((f) => f.code === "POSSIBLE_PERSONAL_DATA" || f.code === "SENSITIVE_CONTENT")

  async function draftWithAi() {
    if (!result) return
    setDrafting(true)
    setDraftError(null)
    try {
      const response = await api.draftWithAi(result.request, asOf || undefined)
      setAck({ text: response.acknowledgement, source: response.ack_source, note: response.ai_note })
      if (!response.ai_available) setDraftError(response.ai_note ?? "AI drafting is not configured; template used")
    } catch (error) {
      setDraftError(error instanceof ApiError ? error.message : "Could not reach the API")
    } finally {
      setDrafting(false)
    }
  }

  async function copy() {
    if (!ack) return
    try {
      await navigator.clipboard.writeText(ack.text)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      setDraftError("Clipboard access was blocked by the browser")
    }
  }

  return (
    <Dialog open={Boolean(result)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="fixed left-[50%] top-[50%] z-[9999] w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg sm:rounded-lg"
        style={{ position: "fixed", margin: "auto" }}
      >
        <div className="thin-scroll -m-6 flex max-h-[85vh] flex-col gap-5 overflow-y-auto p-6">
          <DialogHeader>
            <div className="flex flex-wrap items-center gap-2 pr-8">
              <DialogTitle className="text-xl">{req.request_id || `Row ${req.row_number}`}</DialogTitle>
              <PriorityBadge priority={req.priority} />
              <Badge variant={result.needs_human_review ? "warning" : "success"}>{result.needs_human_review ? "Needs human review" : "Ready to send"}</Badge>
            </div>
            <DialogDescription className="text-left">{req.request_summary || "No summary was provided."}</DialogDescription>
          </DialogHeader>

          <Section title="Request details">
            <dl className="grid grid-cols-2 gap-3 rounded-lg border bg-muted/30 p-3 sm:grid-cols-3">
              <Fact label="Requester role" value={req.requester_role} />
              <Fact label="Submitted" value={result.submitted_date_iso ? formatIsoDate(result.submitted_date_iso) : req.submitted_date} />
              <Fact label="Channel" value={req.channel} />
              <Fact label="Status" value={req.status} />
              <Fact label="Submitted type" value={result.submitted_type} />
              <Fact label="Rule category" value={result.category.category} />
            </dl>
          </Section>

          <Section title="Required information">
            {result.validation_issues.length === 0 ? (
              <p className="flex items-center gap-2 text-sm text-success">
                <ShieldCheck className="size-4" /> All required fields are present and valid.
              </p>
            ) : (
              <ul className="grid gap-1.5">
                {result.validation_issues.map((issue) => (
                  <li key={`${issue.field}-${issue.problem}-${issue.message}`} className="flex items-start gap-2 text-sm">
                    <AlertCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
                    <span>
                      <span className="font-medium">{issue.field}</span> - {issue.message}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section title="How the category was decided">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm">
                <span className="font-medium">{result.category.category}</span>
                {result.category_mismatch && <span className="ml-2 text-amber-700 dark:text-amber-300">differs from submitted type "{result.submitted_type}"</span>}
              </p>
              <ConfidenceDot confidence={result.category.confidence} />
            </div>
            <p className="text-xs text-muted-foreground">{result.category.rationale}</p>
            <ul className="grid gap-1.5">
              {Object.entries(result.category.scores)
                .sort((a, b) => b[1] - a[1])
                .map(([name, score]) => (
                  <li key={name} className="grid grid-cols-[9rem_1fr_2rem] items-center gap-2 text-xs">
                    <span className={cn("truncate", name === result.category.category ? "font-medium" : "text-muted-foreground")}>{name}</span>
                    <div className="h-2 overflow-hidden rounded-full bg-muted">
                      <div
                        className={cn("h-full rounded-full transition-all", name === result.category.category ? "bg-primary" : "bg-muted-foreground/40")}
                        style={{ width: `${(score / maxScore) * 100}%` }}
                      />
                    </div>
                    <span className="text-right tabular-nums text-muted-foreground">{score}</span>
                  </li>
                ))}
            </ul>
            {result.category.matched_keywords.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {result.category.matched_keywords.map((kw) => (
                  <Badge key={kw} variant="outline" className="font-normal">
                    {kw}
                  </Badge>
                ))}
              </div>
            )}
          </Section>

          <Section title="Review flags">
            {result.review_flags.length === 0 ? (
              <p className="text-sm text-muted-foreground">No flags. This request can be acknowledged automatically.</p>
            ) : (
              <ul className="grid gap-2">
                {result.review_flags.map((flag) => (
                  <li key={flag.code} className="grid gap-1 rounded-lg border p-2.5">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={flag.severity} />
                      <span className="font-mono text-xs">{flag.code}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">{flag.reason}</p>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section title="Suggested acknowledgement">
            <div className="flex flex-wrap items-center gap-2">
              <SourceBadge source={ack.source} />
              {ack.note && <span className="text-xs text-muted-foreground">{ack.note}</span>}
            </div>
            <pre className="thin-scroll max-h-72 overflow-auto rounded-lg border bg-muted/40 p-3 font-sans text-sm whitespace-pre-wrap">{ack.text.trim()}</pre>
            {draftError && (
              <p className="flex items-start gap-2 text-xs text-amber-700 dark:text-amber-300">
                <AlertCircle className="mt-0.5 size-3.5 shrink-0" /> {draftError}
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" onClick={copy}>
                {copied ? <Check /> : <Copy />} {copied ? "Copied" : "Copy text"}
              </Button>
              <Button size="sm" onClick={draftWithAi} disabled={drafting || aiBlocked} title={aiBlocked ? "Blocked: the summary may contain personal or sensitive data" : undefined}>
                {drafting ? <Loader2 className="animate-spin" /> : <Sparkles />}
                {health?.ai_configured ? "Draft with AI" : "Try AI draft (not configured)"}
              </Button>
              {aiBlocked && <span className="self-center text-xs text-muted-foreground">AI drafting disabled for this request: possible personal or sensitive data.</span>}
            </div>
          </Section>
        </div>
      </DialogContent>
    </Dialog>
  )
}
