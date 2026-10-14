import { useMemo, useState } from "react"
import { Download, FileJson, FileText, Search, ShieldAlert } from "lucide-react"

import { ConfidenceDot, PriorityBadge, SourceBadge } from "@/components/badges"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { downloadCsv, downloadJson, downloadMarkdown } from "@/lib/download"
import type { TriageResult, TriageRun } from "@/lib/types"
import { cn, formatIsoDate } from "@/lib/utils"

type Filter = "all" | "review" | "ready" | "invalid"

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "review", label: "Needs review" },
  { id: "ready", label: "Ready to send" },
  { id: "invalid", label: "Incomplete" },
]

interface ResultsTableProps {
  run: TriageRun
  onSelect: (result: TriageResult) => void
}

export function ResultsTable({ run, onSelect }: ResultsTableProps) {
  const [filter, setFilter] = useState<Filter>("all")
  const [category, setCategory] = useState<string>("all")
  const [query, setQuery] = useState("")

  const categories = useMemo(() => Object.keys(run.summary.by_category), [run])

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase()
    return run.results.filter((r) => {
      if (filter === "review" && !r.needs_human_review) return false
      if (filter === "ready" && r.needs_human_review) return false
      if (filter === "invalid" && r.is_valid) return false
      if (category !== "all" && r.category.category !== category) return false
      if (q) {
        const haystack = [r.request.request_id, r.request.requester_role, r.request.request_summary, r.category.category, ...r.review_flags.map((f) => f.code)]
          .join(" ")
          .toLowerCase()
        if (!haystack.includes(q)) return false
      }
      return true
    })
  }, [run, filter, category, query])

  const counts: Record<Filter, number> = {
    all: run.results.length,
    review: run.summary.needs_human_review,
    ready: run.summary.auto_acknowledged,
    invalid: run.summary.invalid,
  }

  return (
    <Card>
      <CardHeader className="gap-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">Triage results</CardTitle>
            <CardDescription>
              Click a row for the full decision trail. Assessed as of {formatIsoDate(run.as_of)} ({run.as_of_source}).
            </CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => downloadCsv(run)}>
              <Download /> CSV
            </Button>
            <Button variant="outline" size="sm" onClick={() => downloadJson(run)}>
              <FileJson /> JSON
            </Button>
            <Button variant="outline" size="sm" onClick={() => downloadMarkdown(run, "summary")}>
              <FileText /> Summary
            </Button>
            <Button variant="outline" size="sm" onClick={() => downloadMarkdown(run, "acknowledgements")}>
              <FileText /> Acknowledgements
            </Button>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-lg bg-muted p-[3px]" role="tablist" aria-label="Filter results">
            {FILTERS.map((f) => (
              <button
                key={f.id}
                role="tab"
                aria-selected={filter === f.id}
                onClick={() => setFilter(f.id)}
                className={cn(
                  "inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-md px-3 text-sm font-medium transition-colors",
                  filter === f.id ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {f.label}
                <span className="rounded-full bg-muted-foreground/15 px-1.5 text-[11px] tabular-nums">{counts[f.id]}</span>
              </button>
            ))}
          </div>
          <select
            aria-label="Filter by category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="h-8 rounded-md border bg-background px-2 text-sm shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:bg-input/30"
          >
            <option value="all">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <div className="relative ml-auto w-full sm:w-64">
            <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input aria-label="Search requests" placeholder="Search id, role, summary, flag..." value={query} onChange={(e) => setQuery(e.target.value)} className="h-8 pl-8" />
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-0">
        <Table>
          <TableHeader className="bg-[#fafafa]">
            <TableRow>
              <TableHead className="pl-6">Request</TableHead>
              <TableHead>Submitted</TableHead>
              <TableHead>Role</TableHead>
              <TableHead className="min-w-72">Summary</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Flags</TableHead>
              <TableHead>Ack</TableHead>
              <TableHead className="pr-6 text-right">Review</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={10} className="py-10 text-center text-muted-foreground">
                  No requests match the current filters.
                </TableCell>
              </TableRow>
            )}
            {rows.map((r) => {
              const flags = r.review_flags.filter((f) => f.severity !== "info")
              const critical = flags.filter((f) => f.severity === "critical").length
              return (
                <TableRow
                  key={`${r.request.request_id}-${r.request.row_number}`}
                  tabIndex={0}
                  onClick={() => onSelect(r)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") onSelect(r)
                  }}
                  className="cursor-pointer outline-none focus-visible:bg-muted/60"
                >
                  <TableCell className="pl-6 font-medium">
                    {r.request.request_id || <span className="text-muted-foreground italic">row {r.request.row_number}</span>}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{r.submitted_date_iso ? formatIsoDate(r.submitted_date_iso) : r.request.submitted_date || "-"}</TableCell>
                  <TableCell className="max-w-44 truncate text-muted-foreground">{r.request.requester_role || "-"}</TableCell>
                  <TableCell className="max-w-md whitespace-normal">
                    <p className="line-clamp-2 text-sm leading-snug">{r.request.request_summary || <span className="text-muted-foreground italic">(empty)</span>}</p>
                  </TableCell>
                  <TableCell>
                    <div className="grid gap-0.5">
                      <span className={cn("text-sm", r.category_mismatch && "text-amber-700 dark:text-amber-300")}>{r.category.category}</span>
                      <ConfidenceDot confidence={r.category.confidence} />
                    </div>
                  </TableCell>
                  <TableCell>
                    <PriorityBadge priority={r.request.priority} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">{r.request.status || "-"}</TableCell>
                  <TableCell>
                    {flags.length ? (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="inline-flex items-center gap-1">
                            {critical > 0 && <ShieldAlert className="size-3.5 text-destructive" />}
                            <Badge variant={critical ? "critical" : "warning"}>{flags.length}</Badge>
                          </span>
                        </TooltipTrigger>
                        <TooltipContent>
                          <ul className="grid gap-1">
                            {flags.map((f) => (
                              <li key={f.code}>{f.code}</li>
                            ))}
                          </ul>
                        </TooltipContent>
                      </Tooltip>
                    ) : (
                      <span className="text-xs text-muted-foreground">none</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <SourceBadge source={r.ack_source} />
                  </TableCell>
                  <TableCell className="pr-6 text-right">
                    <Badge variant={r.needs_human_review ? "warning" : "success"}>{r.needs_human_review ? "Human" : "Auto"}</Badge>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
