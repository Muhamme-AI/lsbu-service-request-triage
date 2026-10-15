import { AlertTriangle, CheckCircle2, Inbox, Send, type LucideIcon } from "lucide-react"

import { Card, CardContent } from "@/components/ui/card"
import type { TriageRun } from "@/lib/types"
import { cn } from "@/lib/utils"

interface StatProps {
  icon: LucideIcon
  label: string
  value: number
  hint: string
  accent: string
}

function Stat({ icon: Icon, label, value, hint, accent }: StatProps) {
  return (
    <Card className="gap-0 py-5">
      <CardContent className="flex items-start justify-between gap-3 px-5">
        <div className="grid gap-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
          <p className="text-3xl font-semibold tabular-nums">{value}</p>
          <p className="text-xs text-muted-foreground">{hint}</p>
        </div>
        <div className={cn("flex size-10 shrink-0 items-center justify-center rounded-lg", accent)}>
          <Icon className="size-5" />
        </div>
      </CardContent>
    </Card>
  )
}

export function SummaryCards({ run }: { run: TriageRun }) {
  const s = run.summary
  const sources = Object.entries(s.acknowledgement_sources)
    .map(([k, v]) => `${v} ${k}`)
    .join(", ")
  return (
    <div className="grid min-w-0 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Stat icon={Inbox} label="Requests read" value={s.total} hint={`from ${run.input_file}`} accent="bg-primary/10 text-primary" />
      <Stat
        icon={CheckCircle2}
        label="Complete and valid"
        value={s.valid}
        hint={s.invalid ? `${s.invalid} with missing or invalid information` : "all required information present"}
        accent="bg-success/15 text-success"
      />
      <Stat
        icon={AlertTriangle}
        label="Needs human review"
        value={s.needs_human_review}
        hint={s.category_mismatches ? `${s.category_mismatches} category mismatch${s.category_mismatches === 1 ? "" : "es"}` : "rule categories agree with submitted types"}
        accent="bg-warning/20 text-amber-700 dark:text-amber-300"
      />
      <Stat icon={Send} label="Auto-acknowledged" value={s.auto_acknowledged} hint={`acknowledgements: ${sources}`} accent="bg-chart-2/15 text-chart-2" />
    </div>
  )
}
