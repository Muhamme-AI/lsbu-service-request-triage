import { useCallback, useEffect, useState } from "react"
import { AlertCircle, BookOpenText, Info, LayoutDashboard, Loader2 } from "lucide-react"

import { AboutView } from "@/components/AboutView"
import { AssistantPanel } from "@/components/AssistantPanel"
import { Charts } from "@/components/Charts"
import { Header } from "@/components/Header"
import { RequestDialog } from "@/components/RequestDialog"
import { ResultsTable } from "@/components/ResultsTable"
import { RulesView } from "@/components/RulesView"
import { SummaryCards } from "@/components/SummaryCards"
import { UploadPanel } from "@/components/UploadPanel"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TooltipProvider } from "@/components/ui/tooltip"
import { api, ApiError } from "@/lib/api"
import type { DatasetName, Health, TriageResult, TriageRun } from "@/lib/types"
import { formatIsoDate } from "@/lib/utils"

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [run, setRun] = useState<TriageRun | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<TriageResult | null>(null)
  const [asOf, setAsOf] = useState("")
  const [useAi, setUseAi] = useState(false)
  const [assistantOpen, setAssistantOpen] = useState(false)

  useEffect(() => {
    api
      .health()
      .then(setHealth)
      .catch(() => setError("The API is not reachable. Start it with: uvicorn api.main:app --reload"))
  }, [])

  const execute = useCallback(async (job: () => Promise<TriageRun>) => {
    setLoading(true)
    setError(null)
    try {
      setRun(await job())
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong talking to the API")
    } finally {
      setLoading(false)
    }
  }, [])

  const loadDataset = useCallback((dataset: DatasetName) => execute(() => api.sample(dataset, { asOf, useAi })), [execute, asOf, useAi])
  const loadFile = useCallback((file: File) => execute(() => api.triage(file, { asOf, useAi })), [execute, asOf, useAi])

  return (
    <TooltipProvider>
      <div className="min-h-screen">
        <Header onOpenAssistant={() => setAssistantOpen(true)} />
        <main className="mx-auto grid max-w-7xl gap-6 bg-white px-4 py-6 sm:px-6">
          <Tabs defaultValue="triage">
            <TabsList>
              <TabsTrigger value="triage">
                <LayoutDashboard /> Triage
              </TabsTrigger>
              <TabsTrigger value="rules">
                <BookOpenText /> Rules
              </TabsTrigger>
              <TabsTrigger value="about">
                <Info /> About
              </TabsTrigger>
            </TabsList>

            <TabsContent value="triage" className="grid gap-6 pt-4">
              <UploadPanel
                health={health}
                loading={loading}
                asOf={asOf}
                useAi={useAi}
                onAsOfChange={setAsOf}
                onUseAiChange={setUseAi}
                onFile={loadFile}
                onDataset={loadDataset}
              />

              {error && (
                <div role="alert" className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm">
                  <AlertCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
                  <div>
                    <p className="font-medium text-destructive">Could not triage the file</p>
                    <p className="text-muted-foreground">{error}</p>
                  </div>
                </div>
              )}

              {loading && !run && (
                <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" /> Triaging requests...
                </div>
              )}

              {run && (
                <>
                  <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                    <span>
                      Batch <span className="font-medium text-foreground">{run.input_file}</span> - assessed as of {formatIsoDate(run.as_of)} ({run.as_of_source}) - generated {run.generated_at}
                    </span>
                    {run.missing_columns.length > 0 && <Badge variant="warning">missing columns: {run.missing_columns.join(", ")}</Badge>}
                    {run.ignored_columns.length > 0 && <Badge variant="outline">ignored: {run.ignored_columns.join(", ")}</Badge>}
                    {run.blank_rows_skipped > 0 && <Badge variant="outline">{run.blank_rows_skipped} blank rows skipped</Badge>}
                  </div>
                  <SummaryCards run={run} />
                  <Charts run={run} />
                  <ResultsTable run={run} onSelect={setSelected} />
                </>
              )}

              {!run && !loading && !error && (
                <div className="grid place-items-center gap-2 rounded-lg border border-dashed bg-white py-16 text-center">
                  <p className="font-medium">No batch loaded yet</p>
                  <p className="max-w-md text-sm text-muted-foreground">
                    Load the supplied sample to see a clean batch, or the edge cases to see missing information, personal data, duplicates and ambiguous requests being caught.
                  </p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="rules" className="pt-4">
              <RulesView />
            </TabsContent>

            <TabsContent value="about" className="pt-4">
              <AboutView />
            </TabsContent>
          </Tabs>
        </main>
        <footer className="border-t bg-white">
          <div className="mx-auto max-w-7xl px-4 py-6 text-center text-xs text-muted-foreground sm:px-6">
            Assessment prototype for the AI and Automation Engineer test. Not a live university service. All data is synthetic.
          </div>
        </footer>
        <RequestDialog result={selected} health={health} asOf={asOf} onClose={() => setSelected(null)} />
        <AssistantPanel
          open={assistantOpen}
          onClose={() => setAssistantOpen(false)}
          requests={
            run?.results.map((result) => ({
              request_id: result.request.request_id,
              category: result.category.category,
              priority: result.request.priority,
              status: result.request.status,
              summary: result.request.request_summary,
              flags: result.review_flags.map((flag) => flag.code),
            })) ?? []
          }
        />
      </div>
    </TooltipProvider>
  )
}
