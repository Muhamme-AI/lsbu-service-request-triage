// Mirrors the JSON produced by triage/report.py::run_to_dict and api/main.py::serialise.

export interface RequestRow {
  row_number: number
  request_id: string
  submitted_date: string
  requester_role: string
  request_type: string
  request_summary: string
  priority: string
  channel: string
  status: string
}

export interface ValidationIssue {
  field: string
  problem: "missing" | "invalid"
  message: string
}

export type Confidence = "high" | "medium" | "low" | "none"

export interface CategoryResult {
  category: string
  confidence: Confidence
  score: number
  matched_keywords: string[]
  scores: Record<string, number>
  rationale: string
}

export type Severity = "critical" | "warning" | "info"

export interface ReviewFlag {
  code: string
  severity: Severity
  reason: string
}

export interface TriageResult {
  request: RequestRow
  submitted_date_iso: string | null
  is_valid: boolean
  validation_issues: ValidationIssue[]
  category: CategoryResult
  submitted_type: string
  category_mismatch: boolean
  acknowledgement: string
  ack_source: "template" | "ai"
  ai_note: string | null
  needs_human_review: boolean
  review_flags: ReviewFlag[]
}

export interface TriageSummary {
  total: number
  valid: number
  invalid: number
  needs_human_review: number
  auto_acknowledged: number
  category_mismatches: number
  by_category: Record<string, number>
  by_priority: Record<string, number>
  by_channel: Record<string, number>
  by_status: Record<string, number>
  review_flags: Record<string, number>
  acknowledgement_sources: Record<string, number>
}

export interface TriageRun {
  generated_at: string
  input_file: string
  rules_version: string
  as_of: string
  as_of_source: string
  ai_enabled: boolean
  ai_provider: string | null
  columns_found: string[]
  missing_columns: string[]
  ignored_columns: string[]
  blank_rows_skipped: number
  summary: TriageSummary
  results: TriageResult[]
  markdown: {
    summary: string
    acknowledgements: string
  }
}

export interface Health {
  status: string
  version: string
  ai_configured: boolean
  ai_provider: string | null
  ai_fallbacks?: string[]
  ai_chain?: string | null
  ai_problem: string | null
}

export interface RuleCategory {
  name: string
  description?: string
  strong: string[]
  weak: string[]
}

export interface RulesPayload {
  rules: {
    version: string
    description?: string
    categorisation: {
      fallback_category: string
      strong_weight: number
      weak_weight: number
      leading_verb_bonus: number
      leading_words: number
      high_confidence_margin: number
      minimum_confident_score: number
      categories: RuleCategory[]
    }
    validation: {
      required_fields: string[]
      optional_fields: string[]
      request_id_pattern: string
      date_formats: string[]
      allow_future_dates: boolean
      minimum_summary_length: number
      allowed_priorities: string[]
      allowed_channels: string[]
      allowed_statuses: string[]
    }
    review: {
      overdue_days: number
      overdue_statuses: string[]
      attention_priorities: string[]
      external_access_keywords: string[]
      sensitive_keywords: string[]
      credential_keywords: string[]
      personal_data_patterns: Record<string, string>
    }
  }
  acknowledgements: {
    sender: string
    response_targets: Record<string, string>
    template: string
    category_notes: Record<string, string>
    incomplete_note: string
  }
}

export interface AssistantSource {
  source: string
  excerpt: string
}

export interface AssistantResponse {
  reply: string
  sources: AssistantSource[]
  refused: boolean
  reason: string | null
  model: string | null
  matched_requests: string[]
}

export interface AssistantIndexStats {
  path: string
  chunks: number
  sources: Record<string, number>
  vocabulary: number
  index_version: string
}

export interface AssistantRequestFact {
  request_id: string
  category: string
  priority: string
  status: string
  summary: string
  flags: string[]
}

export interface AIDraftResponse {
  ai_available: boolean
  acknowledgement: string
  ack_source: "template" | "ai"
  ai_note: string | null
}

export type DatasetName = "sample" | "edge-cases"
