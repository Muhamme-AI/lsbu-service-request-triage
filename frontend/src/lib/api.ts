import type { AIDraftResponse, AssistantRequestFact, AssistantResponse, DatasetName, Health, RequestRow, RulesPayload, TriageRun } from "./types"

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === "string") detail = body.detail
      else if (Array.isArray(body.detail)) detail = body.detail.map((d) => (d as { msg?: string }).msg ?? JSON.stringify(d)).join("; ")
    } catch {
      // keep statusText
    }
    throw new ApiError(response.status, detail || `Request failed (${response.status})`)
  }
  return (await response.json()) as T
}

function withParams(path: string, params: Record<string, string | boolean | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === "" || value === false) continue
    search.set(key, String(value))
  }
  const query = search.toString()
  return query ? `${path}?${query}` : path
}

export interface RunOptions {
  asOf?: string
  useAi?: boolean
}

export const api = {
  health: () => fetch("/api/health").then((r) => parse<Health>(r)),
  rules: () => fetch("/api/rules").then((r) => parse<RulesPayload>(r)),
  sample: (dataset: DatasetName, options: RunOptions = {}) =>
    fetch(withParams("/api/sample", { dataset, as_of: options.asOf, use_ai: options.useAi })).then((r) => parse<TriageRun>(r)),
  triage: (file: File, options: RunOptions = {}) => {
    const body = new FormData()
    body.append("file", file, file.name)
    return fetch(withParams("/api/triage", { as_of: options.asOf, use_ai: options.useAi }), { method: "POST", body }).then((r) =>
      parse<TriageRun>(r),
    )
  },
  assistant: (question: string, history: { role: string; content: string }[], requests: AssistantRequestFact[]) =>
    fetch("/api/assistant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history, requests }),
    }).then((r) => parse<AssistantResponse>(r)),
  draftWithAi: (request: RequestRow, asOf?: string) =>
    fetch("/api/acknowledgement/ai", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request, as_of: asOf || null }),
    }).then((r) => parse<AIDraftResponse>(r)),
}
