import { useEffect, useRef, useState } from "react"
import { BookOpenCheck, Check, Copy, Eraser, Loader2, Send, ShieldAlert, WandSparkles, X } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { api, ApiError } from "@/lib/api"
import type { AssistantIndexStats, AssistantRequestFact, AssistantSource } from "@/lib/types"
import { cn } from "@/lib/utils"

interface Message {
  role: "user" | "assistant"
  content: string
  sources?: AssistantSource[]
  refused?: boolean
  reason?: string | null
  model?: string | null
  matched?: string[]
}

interface AssistantPanelProps {
  open: boolean
  requests: AssistantRequestFact[]
  onClose: () => void
}

const STARTERS = [
  "Which requests should I look at first, and why?",
  "What do I check before approving external access?",
  "Draft a reply for the oldest high priority request.",
  "Which requests are missing information?",
]

const REASON_LABELS: Record<string, string> = {
  PROMPT_INJECTION: "Instruction override blocked",
  SECRET_REQUEST: "Secrets are not shared",
  PERSONAL_DATA: "Personal data removed",
  OFF_TOPIC: "Outside the queue",
  EMPTY_QUESTION: "Nothing to answer",
  TOO_LONG: "Message too long",
  SEND_CLAIM: "Model reply dropped: claimed to send",
  ACTION_CLAIM: "Model reply dropped: claimed to act",
  UNKNOWN_REFERENCE: "Model reply dropped: invented a request",
  NOT_PLAIN_TEXT: "Model reply dropped: not plain text",
  CREDENTIAL: "Model reply dropped: credential",
  TOO_SHORT: "Model reply dropped: empty",
  PROVIDER_UNAVAILABLE: "Model unavailable, guidance shown",
}

function looksLikeDraft(text: string): boolean {
  return /dear colleague/i.test(text) && /digital services team/i.test(text)
}

function extractDraft(text: string): string {
  const start = text.search(/dear colleague/i)
  if (start < 0) return text
  const body = text.slice(start)
  const end = body.search(/\n\s*(reviewer|please check|check this draft)/i)
  return (end > 0 ? body.slice(0, end) : body).trim()
}

export function AssistantPanel({ open, requests, onClose }: AssistantPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [question, setQuestion] = useState("")
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)
  const [index, setIndex] = useState<AssistantIndexStats | null>(null)
  const scroller = useRef<HTMLDivElement>(null)
  const field = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!open) return
    field.current?.focus()
    if (!index) api.assistantIndex().then(setIndex).catch(() => setIndex(null))
  }, [open, index])

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" })
  }, [messages, sending])

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open, onClose])

  if (!open) return null

  async function send(text: string) {
    const trimmed = text.trim()
    if (!trimmed || sending) return
    const history = messages.filter((m) => !m.refused).map(({ role, content }) => ({ role, content }))
    setMessages((current) => [...current, { role: "user", content: trimmed }])
    setQuestion("")
    setSending(true)
    setError(null)
    try {
      const response = await api.assistant(trimmed, history, requests)
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.reply,
          sources: response.sources,
          refused: response.refused,
          reason: response.reason,
          model: response.model,
          matched: response.matched_requests,
        },
      ])
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The assistant could not be reached")
    } finally {
      setSending(false)
    }
  }

  async function copyDraft(text: string, messageIndex: number) {
    try {
      await navigator.clipboard.writeText(extractDraft(text))
      setCopiedIndex(messageIndex)
      window.setTimeout(() => setCopiedIndex(null), 1500)
    } catch {
      setError("Clipboard access was blocked by the browser")
    }
  }

  return (
    <aside className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l bg-white shadow-xl" aria-label="Review assistant" role="dialog">
      <div className="flex items-center justify-between gap-3 border-b bg-primary px-4 py-3 text-primary-foreground">
        <div className="flex items-center gap-2">
          <WandSparkles className="size-4" />
          <div>
            <p className="text-sm font-semibold">Review assistant</p>
            <p className="text-[11px] text-white/80">
              {requests.length ? `${requests.length} requests in context` : "No batch loaded - guidance only"}
              {index ? ` · ${index.chunks} guidance chunks indexed` : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <Button variant="ghost" size="icon" className="text-white hover:bg-white/15 hover:text-white" onClick={() => setMessages([])} aria-label="Clear the conversation">
              <Eraser />
            </Button>
          )}
          <Button variant="ghost" size="icon" className="text-white hover:bg-white/15 hover:text-white" onClick={onClose} aria-label="Close the review assistant">
            <X />
          </Button>
        </div>
      </div>

      <div ref={scroller} className="thin-scroll flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="grid gap-3 text-sm text-muted-foreground">
            <p>Ask what to do with a request, which rule applies, or ask for a draft reply. Drafts stay in this chat until you copy them. Nothing is sent from here.</p>
            <div className="flex flex-wrap gap-2">
              {STARTERS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="rounded-full border px-3 py-1 text-left text-xs text-foreground hover:bg-muted"
                  onClick={() => void send(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
            <p className="flex items-start gap-1.5 text-xs">
              <ShieldAlert className="mt-0.5 size-3.5 shrink-0 text-primary" />
              Personal data is redacted before anything reaches the model. Replies that claim to have sent or changed something are discarded.
            </p>
          </div>
        )}

        {messages.map((message, messageIndex) => {
          const isUser = message.role === "user"
          const draft = !isUser && !message.refused && looksLikeDraft(message.content)
          return (
            <div key={`${message.role}-${messageIndex}`} className={isUser ? "ml-8" : "mr-4"}>
              <div
                className={cn(
                  "rounded-lg px-3 py-2 text-sm",
                  isUser ? "bg-primary text-primary-foreground" : "border bg-white",
                  message.refused && "border-amber-300 bg-amber-50",
                )}
              >
                {message.refused && message.reason && (
                  <p className="mb-1 flex items-center gap-1 text-[11px] font-medium text-amber-800">
                    <ShieldAlert className="size-3" /> {REASON_LABELS[message.reason] ?? message.reason}
                  </p>
                )}
                {!message.refused && message.reason === "PROVIDER_UNAVAILABLE" && (
                  <p className="mb-1 text-[11px] font-medium text-muted-foreground">{REASON_LABELS.PROVIDER_UNAVAILABLE}</p>
                )}
                <p className="whitespace-pre-wrap">{message.content}</p>
              </div>
              {!isUser && (
                <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                  {message.sources?.map((source) => (
                    <Badge key={source.source} variant="outline" className="gap-1 font-normal" title={source.excerpt}>
                      <BookOpenCheck className="size-3" /> {source.source}
                    </Badge>
                  ))}
                  {message.matched && message.matched.length > 0 && <span>Looked at {message.matched.slice(0, 3).join(", ")}</span>}
                  {message.model && <span>via {message.model}</span>}
                  {draft && (
                    <Button variant="outline" size="sm" className="ml-auto h-6 gap-1 px-2 text-[11px]" onClick={() => void copyDraft(message.content, messageIndex)}>
                      {copiedIndex === messageIndex ? <Check className="size-3" /> : <Copy className="size-3" />}
                      {copiedIndex === messageIndex ? "Copied" : "Copy draft"}
                    </Button>
                  )}
                </div>
              )}
            </div>
          )
        })}

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
          void send(question)
        }}
      >
        <textarea
          ref={field}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault()
              void send(question)
            }
          }}
          rows={2}
          maxLength={2000}
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
