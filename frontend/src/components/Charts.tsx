import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip as ChartTooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import type { TriageRun } from "@/lib/types"

const PALETTE = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--muted-foreground)"]
const PRIORITY_COLOURS: Record<string, string> = {
  High: "var(--primary)",
  Medium: "var(--warning)",
  Low: "var(--success)",
}

function toSeries(record: Record<string, number>) {
  return Object.entries(record).map(([name, value]) => ({ name, value }))
}

const tooltipStyle = {
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--popover)",
  color: "var(--popover-foreground)",
  fontSize: 12,
}

export function Charts({ run }: { run: TriageRun }) {
  const byCategory = toSeries(run.summary.by_category)
  const byPriority = toSeries(run.summary.by_priority)
  const byFlag = toSeries(run.summary.review_flags)

  return (
    <div className="grid min-w-0 gap-4 lg:grid-cols-3">
      <Card className="gap-4">
        <CardHeader>
          <CardTitle className="text-sm">Requests by rule category</CardTitle>
          <CardDescription>Decided by keyword rules in config/rules.json</CardDescription>
        </CardHeader>
        <CardContent className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={byCategory} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
              <XAxis type="number" allowDecimals={false} hide />
              <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
              <ChartTooltip cursor={{ fill: "var(--muted)" }} contentStyle={tooltipStyle} />
              <Bar dataKey="value" radius={[0, 6, 6, 0]} isAnimationActive={false}>
                {byCategory.map((_, index) => (
                  <Cell key={index} fill={PALETTE[index % PALETTE.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="gap-4">
        <CardHeader>
          <CardTitle className="text-sm">Requests by priority</CardTitle>
          <CardDescription>High priority always goes to a person</CardDescription>
        </CardHeader>
        <CardContent className="flex h-56 items-center gap-4">
          <div className="h-full flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <ChartTooltip contentStyle={tooltipStyle} />
                <Pie data={byPriority} dataKey="value" nameKey="name" innerRadius="55%" outerRadius="85%" paddingAngle={3} stroke="var(--card)" isAnimationActive={false}>
                  {byPriority.map((entry, index) => (
                    <Cell key={entry.name} fill={PRIORITY_COLOURS[entry.name] ?? PALETTE[index % PALETTE.length]} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
          <ul className="grid gap-2 text-sm">
            {byPriority.map((entry, index) => (
              <li key={entry.name} className="flex items-center gap-2">
                <span className="size-2.5 rounded-full" style={{ background: PRIORITY_COLOURS[entry.name] ?? PALETTE[index % PALETTE.length] }} />
                <span className="text-muted-foreground">{entry.name}</span>
                <span className="ml-auto font-medium tabular-nums">{entry.value}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card className="gap-4">
        <CardHeader>
          <CardTitle className="text-sm">Why requests need a person</CardTitle>
          <CardDescription>{byFlag.length ? "Review flags raised across the batch" : "No review flags raised"}</CardDescription>
        </CardHeader>
        <CardContent className="h-56">
          {byFlag.length ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={byFlag} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
                <XAxis type="number" allowDecimals={false} hide />
                <YAxis type="category" dataKey="name" width={170} tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
                <ChartTooltip cursor={{ fill: "var(--muted)" }} contentStyle={tooltipStyle} />
                <Bar dataKey="value" radius={[0, 6, 6, 0]} fill="var(--foreground)" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">Every request can be acknowledged automatically.</div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
