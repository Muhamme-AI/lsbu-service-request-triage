import { ClipboardCheck, Github, Sparkles } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import type { Health } from "@/lib/types"

export const REPO_URL = "https://github.com/Muhamme-AI/lsbu-service-request-triage"

interface HeaderProps {
  health: Health | null
}

export function Header({ health }: HeaderProps) {
  const aiLabel = health === null ? "Connecting to API..." : health.ai_configured ? `AI drafting: ${health.ai_provider}` : "AI drafting: off (templates)"
  const fallbacks = health?.ai_fallbacks ?? []
  const usingGroq = Boolean(health?.ai_provider?.startsWith("groq"))
  const aiTip =
    health === null
      ? "Waiting for /api/health"
      : health.ai_configured && usingGroq
        ? `Free model via Groq. ${fallbacks.length ? `If Groq fails it tries ${fallbacks.join(", ")}, then the template.` : "Azure OpenAI and OpenAI are the fallback when those keys are set. The template is used if the model is unavailable."} Personal or sensitive requests are never sent.`
        : health.ai_configured
          ? `Acknowledgements can be refined by ${health.ai_provider}. Personal or sensitive requests are never sent.`
          : health.ai_problem
            ? `AI provider mis-configured: ${health.ai_problem}`
            : "Set TRIAGE_AI_PROVIDER=groq and GROQ_API_KEY in .env. Azure OpenAI and OpenAI can be added as the fallback."

  return (
    <header className="sticky top-0 z-40 bg-primary text-primary-foreground">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3.5 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-md bg-white/15">
            <ClipboardCheck className="size-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-white/80">London South Bank University</p>
            <h1 className="text-base font-semibold leading-tight sm:text-lg">Service Request Triage</h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Badge variant="outline" className="hidden gap-1.5 border-white/30 bg-white/10 px-2.5 py-1 text-white sm:inline-flex">
                <Sparkles className="size-3" />
                {aiLabel}
              </Badge>
            </TooltipTrigger>
            <TooltipContent>{aiTip}</TooltipContent>
          </Tooltip>
          <Button variant="ghost" size="icon" className="text-white hover:bg-white/15 hover:text-white" asChild aria-label="Open the GitHub repository">
            <a href={REPO_URL} target="_blank" rel="noreferrer">
              <Github />
            </a>
          </Button>
        </div>
      </div>
    </header>
  )
}
