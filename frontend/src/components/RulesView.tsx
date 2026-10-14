import { useEffect, useState } from "react"
import { BookOpenText, Loader2, ScanSearch, ShieldAlert, SlidersHorizontal } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { api, ApiError } from "@/lib/api"
import type { RulesPayload } from "@/lib/types"

function Chips({ items, variant = "secondary" }: { items: string[]; variant?: "secondary" | "default" | "outline" }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <Badge key={item} variant={variant} className="font-normal">
          {item}
        </Badge>
      ))}
    </div>
  )
}

function Setting({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid gap-1">
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm">{value}</dd>
    </div>
  )
}

export function RulesView() {
  const [data, setData] = useState<RulesPayload | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .rules()
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not load the rules from the API"))
  }, [])

  if (error) return <p className="text-sm text-destructive">{error}</p>
  if (!data)
    return (
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Loading rules...
      </p>
    )

  const { categorisation, validation, review } = data.rules
  const ack = data.acknowledgements

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <SlidersHorizontal className="size-4 text-primary" /> How scoring works
          </CardTitle>
          <CardDescription>Everything on this page comes from config/rules.json and config/acknowledgements.json - no code changes needed to tune it.</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Setting label="Strong keyword" value={`+${categorisation.strong_weight} points`} />
            <Setting label="Weak keyword" value={`+${categorisation.weak_weight} point`} />
            <Setting label="Opening verb bonus" value={`+${categorisation.leading_verb_bonus} if a strong keyword is in the first ${categorisation.leading_words} words`} />
            <Setting label="Confidence" value={`high when the winner leads by ${categorisation.high_confidence_margin}+ and scores ${categorisation.minimum_confident_score}+; ties or weak matches are low and go to a person`} />
          </dl>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {categorisation.categories.map((category) => (
          <Card key={category.name} className="gap-4">
            <CardHeader>
              <CardTitle className="text-sm">{category.name}</CardTitle>
              {category.description && <CardDescription>{category.description}</CardDescription>}
            </CardHeader>
            <CardContent className="grid gap-3">
              <div className="grid gap-1.5">
                <p className="text-xs font-medium text-muted-foreground">Strong (+{categorisation.strong_weight})</p>
                <Chips items={category.strong} variant="default" />
              </div>
              <div className="grid gap-1.5">
                <p className="text-xs font-medium text-muted-foreground">Weak (+{categorisation.weak_weight})</p>
                <Chips items={category.weak} />
              </div>
            </CardContent>
          </Card>
        ))}
        <Card className="gap-4 border-dashed">
          <CardHeader>
            <CardTitle className="text-sm">{categorisation.fallback_category}</CardTitle>
            <CardDescription>Used when no keyword matches. Always routed to a person.</CardDescription>
          </CardHeader>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ScanSearch className="size-4 text-primary" /> Required information
            </CardTitle>
            <CardDescription>Checked before anything else; failures are critical review flags.</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-4">
              <Setting label="Required fields" value={<Chips items={validation.required_fields} />} />
              <Setting label="Optional" value={<Chips items={validation.optional_fields} variant="outline" />} />
              <Setting label="Request ID format" value={<code className="rounded bg-muted px-1.5 py-0.5 text-xs">{validation.request_id_pattern}</code>} />
              <Setting label="Date formats" value={<Chips items={validation.date_formats} variant="outline" />} />
              <Setting label="Minimum summary length" value={`${validation.minimum_summary_length} characters`} />
              <Setting label="Priorities" value={<Chips items={validation.allowed_priorities} />} />
              <Setting label="Channels" value={<Chips items={validation.allowed_channels} />} />
              <Setting label="Statuses" value={<Chips items={validation.allowed_statuses} />} />
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldAlert className="size-4 text-primary" /> Human review triggers
            </CardTitle>
            <CardDescription>Any warning or critical flag sends the request to a person.</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-4">
              <Setting label="Overdue" value={`status ${review.overdue_statuses.join(" / ")} for more than ${review.overdue_days} days`} />
              <Setting label="Priorities needing attention" value={<Chips items={review.attention_priorities} />} />
              <Setting label="External access words" value={<Chips items={review.external_access_keywords} variant="outline" />} />
              <Setting label="Sensitive content words" value={<Chips items={review.sensitive_keywords} variant="outline" />} />
              <Setting label="Credential words" value={<Chips items={review.credential_keywords} variant="outline" />} />
              <Setting label="Personal data patterns" value={<Chips items={Object.keys(review.personal_data_patterns)} variant="outline" />} />
            </dl>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BookOpenText className="size-4 text-primary" /> Acknowledgement template
          </CardTitle>
          <CardDescription>Response targets: {Object.entries(ack.response_targets).map(([k, v]) => `${k}: ${v}`).join(" | ")}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-2">
          <pre className="thin-scroll overflow-auto rounded-lg border bg-muted/40 p-3 font-sans text-sm whitespace-pre-wrap">{ack.template}</pre>
          <dl className="grid gap-3">
            {Object.entries(ack.category_notes).map(([name, note]) => (
              <Setting key={name} label={name} value={note} />
            ))}
            <Setting label="When information is missing" value={ack.incomplete_note} />
          </dl>
        </CardContent>
      </Card>
    </div>
  )
}
