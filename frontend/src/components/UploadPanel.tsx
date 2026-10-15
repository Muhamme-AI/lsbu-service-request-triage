import { useCallback, useId, useRef, useState } from "react"
import { CalendarDays, Database, FileSpreadsheet, FlaskConical, Loader2, Sparkles, UploadCloud } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import type { DatasetName, Health } from "@/lib/types"
import { cn } from "@/lib/utils"

interface UploadPanelProps {
  health: Health | null
  loading: boolean
  asOf: string
  useAi: boolean
  onAsOfChange: (value: string) => void
  onUseAiChange: (value: boolean) => void
  onFile: (file: File) => void
  onDataset: (dataset: DatasetName) => void
}

export function UploadPanel({ health, loading, asOf, useAi, onAsOfChange, onUseAiChange, onFile, onDataset }: UploadPanelProps) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const asOfId = useId()
  const aiId = useId()
  const aiAvailable = Boolean(health?.ai_configured)

  const handleFiles = useCallback(
    (files: FileList | null) => {
      const file = files?.[0]
      if (file) onFile(file)
    },
    [onFile],
  )

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <FileSpreadsheet className="size-4 text-primary" />
          Load a batch of requests
        </CardTitle>
        <CardDescription>
          Drop a CSV exported from the team's spreadsheet, or use one of the synthetic data sets. Nothing is uploaded anywhere except the local API.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <div
          role="button"
          tabIndex={0}
          aria-label="Choose a CSV file"
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault()
              inputRef.current?.click()
            }
          }}
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragging(false)
            handleFiles(e.dataTransfer.files)
          }}
          className={cn(
            "group flex min-h-44 cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-6 text-center transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
            dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/60 hover:bg-muted/40",
          )}
        >
          <div className="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary transition-transform group-hover:scale-105">
            {loading ? <Loader2 className="size-6 animate-spin" /> : <UploadCloud className="size-6" />}
          </div>
          <div>
            <p className="font-medium">{dragging ? "Release to triage this file" : "Drag and drop a CSV here"}</p>
            <p className="text-sm text-muted-foreground">or click to browse. Expected columns: Request ID, Submitted Date, Requester Role, Request Type, Request Summary, Priority, Channel, Status.</p>
          </div>
          <input ref={inputRef} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => handleFiles(e.target.files)} />
        </div>

        <div className="flex flex-col gap-5">
          <div className="grid gap-2">
            <p className="text-sm font-medium">Synthetic data sets</p>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
              <Button variant="outline" className="justify-start" disabled={loading} onClick={() => onDataset("sample")}>
                <Database className="text-primary" />
                Supplied sample
                <span className="ml-auto text-xs text-muted-foreground">10 rows</span>
              </Button>
              <Button variant="outline" className="justify-start" disabled={loading} onClick={() => onDataset("edge-cases")}>
                <FlaskConical className="text-chart-3" />
                Edge cases
                <span className="ml-auto text-xs text-muted-foreground">15 rows</span>
              </Button>
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor={asOfId} className="text-sm">
              <CalendarDays className="size-4 text-muted-foreground" />
              Assess dates as of
            </Label>
            <Input id={asOfId} type="date" value={asOf} onChange={(e) => onAsOfChange(e.target.value)} className="w-full" />
            <p className="text-xs text-muted-foreground">Leave blank to use the latest submission date in the file (reproducible). Used for future-date and overdue checks.</p>
          </div>

          <div className="flex items-center justify-between gap-3 rounded-lg border p-3">
            <Label htmlFor={aiId} className="text-sm">
              <Sparkles className="size-4 text-primary" />
              Refine acknowledgements with AI
            </Label>
            <Switch id={aiId} checked={useAi && aiAvailable} disabled={!aiAvailable || loading} onCheckedChange={onUseAiChange} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
