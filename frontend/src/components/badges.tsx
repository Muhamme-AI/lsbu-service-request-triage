import { Badge } from "@/components/ui/badge"
import type { Confidence, Severity } from "@/lib/types"

export function PriorityBadge({ priority }: { priority: string }) {
  const key = priority.toLowerCase()
  const variant = key === "high" ? "critical" : key === "medium" ? "warning" : key === "low" ? "success" : "outline"
  return <Badge variant={variant}>{priority || "-"}</Badge>
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const variant = severity === "critical" ? "critical" : severity === "warning" ? "warning" : "info"
  return (
    <Badge variant={variant} className="uppercase tracking-wide">
      {severity}
    </Badge>
  )
}

export function ConfidenceDot({ confidence }: { confidence: Confidence }) {
  const colour =
    confidence === "high" ? "bg-success" : confidence === "medium" ? "bg-chart-3" : confidence === "low" ? "bg-destructive" : "bg-muted-foreground"
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground" title={`${confidence} confidence`}>
      <span className={`size-2 rounded-full ${colour}`} />
      {confidence}
    </span>
  )
}

export function SourceBadge({ source }: { source: "template" | "ai" }) {
  return <Badge variant={source === "ai" ? "default" : "secondary"}>{source === "ai" ? "AI draft" : "template"}</Badge>
}
