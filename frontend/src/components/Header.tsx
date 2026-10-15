import { ClipboardCheck, Github, WandSparkles } from "lucide-react"

import { Button } from "@/components/ui/button"

export const REPO_URL = "https://github.com/Muhamme-AI/lsbu-service-request-triage"

interface HeaderProps {
  onOpenAssistant: () => void
}

export function Header({ onOpenAssistant }: HeaderProps) {
  return (
    <header className="sticky top-0 z-40 flex h-[4.25rem] items-center bg-primary text-primary-foreground">
      <div className="mx-auto flex h-full w-full max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
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
          <Button variant="ghost" className="text-white hover:bg-white/15 hover:text-white" onClick={onOpenAssistant}>
            <WandSparkles />
            <span className="hidden sm:inline">AI wizard</span>
          </Button>
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
