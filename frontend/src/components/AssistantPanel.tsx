import { useEffect, useRef, useState } from "react"
import { Loader2, Send, WandSparkles, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { api, ApiError } from "@/lib/api"
import type { AssistantRequestFact, AssistantSource } from "@/lib/types"

interface Message {
  role: "user" | "assistant"
  content: string
  sources?: AssistantSource[]
}

interface AssistantPanelProps {
  open: boolean
  requests: AssistantRequestFact[]
  onClose: () => void
}

export function AssistantPanel({ open, requests, onClose }: AssistantPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [question, setQuestion] = useState("")
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const scroller = useRef<HTMLDivElement>(null)
  const field = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (open) field.current?.focus()
  }, [open])

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight })
  }, [messages, sending])

  if (!open) return null

  async function send() {
    const text = question.trim()
    if (!text || sending) return
    const history = messages.map(({ role, content }) => ({ role, content }))
    setMessages((current) => [...current, { role: "user", content: text }])
    setQuestion("")
    setSending(true)
    setError(null)
    try {
      const response = await api.assistant(text, history, requests)
      setMessages((current) => [...current, { role: "assistant", content: response.reply, sources: response.sources }])
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The assistant could not be reached")
    } finally {
      setSending(false)
    }
  }

  return (
    <aside className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l bg-white shadow-xl" aria-label="Review assistant">
      <div className="flex items-center justify-between gap-3 border-b bg-primary px-4 py-3 text-primary-foreground">
        <div className="flex items-center gap-2">
          <WandSparkles className="size-4" />
          <div>
            <p className="text-sm font-semibold">Review assistant</p>
            <p className="text-[11px] text-white/80">{requests.length ? `${requests.length} requests in context` : "Guidance only, no batch loaded"}</p>
          </div>
        </div>
        <Button variant="ghost" size="icon" className="text-white hover:bg-white/15 hover:text-white" onClick={onClose} aria-label="Close the review assistant">
          <X />
        </Button>
      </div>
      <div ref={scroller} className="thin-scroll flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="grid gap-2 text-sm text-muted-foreground">
            <p>Ask what to do with a request, or ask for a draft reply. Drafts stay in this chat until you check them.</p>
            <div className="flex flex-wrap gap-2">
              {["What should I check before external access?", "Draft a reply for the oldest high priority request"].map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="rounded-full border px-3 py-1 text-left text-xs text-foreground hover:bg-muted"
                  onClick={() => setQuestion(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={message.role === "user" ? "ml-8" : "mr-4"}>
            <div className={message.role === "user" ? "rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground" : "rounded-lg border bg-white px-3 py-2 text-sm"}>
              <p className="whitespace-pre-wrap">{message.content}</p>
            </div>
            {message.sources && message.sources.length > 0 && (
              <ul className="mt-1 grid gap-0.5 text-[11px] text-muted-foreground">
                {message.sources.map((source) => (
                  <li key={source.source}>From {source.source}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
        {sending && (
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" /> Looking up the guidance
          </p>
        )}
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
      <form
        className="flex items-end gap-2 border-t p-3"
        onSubmit={(event) => {
          event.preventDefault()
          void send()
        }}
      >
        <textarea
          ref={field}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault()
              void send()
            }
          }}
          rows={2}
          placeholder="Ask about a request, or ask for a draft email"
          aria-label="Message the review assistant"
          className="min-h-16 flex-1 resize-none rounded-md border bg-white px-3 py-2 text-sm outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
        />
        <Button type="submit" size="icon" disabled={sending || !question.trim()} aria-label="Send">
          <Send />
        </Button>
      </form>
    </aside>
  )
}
