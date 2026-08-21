/**
 * TypeScript mirrors of the FastAPI Pydantic schemas (api/schema.py).
 * Fields are typed defensively (optional) because the backend evolves; the UI
 * renders only what is actually present and never fabricates values.
 */

export interface SimilarStory {
  title?: string;
  url?: string | null;
  points?: number | null;
  num_comments?: number | null;
  comments?: number | null;
  story_id?: number | string | null;
  objectID?: string | null;
  domain?: string | null;
  created_at?: string | null;
  similarity?: number | null;
  score?: number | null;
}

export interface PostingTime {
  day?: string | null;
  day_of_week?: string | null;
  hour?: number | null;
  hour_utc?: number | null;
  window?: string | null;
  window_utc?: string | null;
  avg_points?: number | null;
  story_count?: number | null;
}

export interface TitleAnalysis {
  title?: string;
  pattern_score?: number | null;
  score?: number | null;
  structural_score?: number | null;
  matched_phrases?: string[] | null;
  matched_topics?: string[] | null;
  structural_flags?: string[] | null;
  title_length?: number | null;
  title_word_count?: number | null;
  similar_stories?: SimilarStory[] | null;
  best_posting_time?: PostingTime | null;
  recommended_posting_time?: PostingTime | null;
  [key: string]: unknown;
}

export type Trajectory = "rising" | "falling" | "stable" | string;

export interface MonitorSnapshot {
  story_id?: number | string;
  title?: string | null;
  url?: string | null;
  points?: number | null;
  num_comments?: number | null;
  comments?: number | null;
  rank?: number | null;
  approx_rank?: number | null;
  age_minutes?: number | null;
  created_at?: string | null;
  points_velocity?: number | null;
  comments_velocity?: number | null;
  rank_change?: number | null;
  engagement_ratio?: number | null;
  viral_probability?: number | null;
  probability?: number | null;
  previous_probability?: number | null;
  probability_delta?: number | null;
  delta?: number | null;
  trajectory?: Trajectory | null;
  features?: Record<string, number> | null;
  observed_at?: string | null;
  timestamp?: string | null;
  [key: string]: unknown;
}

export interface MonitorHistoryPoint {
  timestamp?: string | null;
  observed_at?: string | null;
  time?: string | null;
  viral_probability?: number | null;
  probability?: number | null;
  points?: number | null;
  num_comments?: number | null;
  comments?: number | null;
  rank?: number | null;
  [key: string]: unknown;
}

export interface MonitorHistory {
  story_id?: number | string;
  history?: MonitorHistoryPoint[] | null;
  entries?: MonitorHistoryPoint[] | null;
  count?: number | null;
  [key: string]: unknown;
}

export interface TrendingTopic {
  topic?: string | null;
  phrase?: string | null;
  keyword?: string | null;
  score?: number | null;
  story_count?: number | null;
  count?: number | null;
  total_points?: number | null;
  points?: number | null;
  [key: string]: unknown;
}

export interface TrendingResponse {
  topics?: TrendingTopic[] | null;
  trending?: TrendingTopic[] | null;
  hours?: number | null;
  generated_at?: string | null;
  [key: string]: unknown;
}

export interface DomainStat {
  domain?: string | null;
  avg_peak_points?: number | null;
  avg_points?: number | null;
  story_count?: number | null;
  count?: number | null;
  [key: string]: unknown;
}

export interface DomainsResponse {
  domains?: DomainStat[] | null;
  [key: string]: unknown;
}

export interface BestTimeSlot {
  day?: string | null;
  day_of_week?: string | null;
  hour?: number | null;
  hour_utc?: number | null;
  avg_points?: number | null;
  story_count?: number | null;
  [key: string]: unknown;
}

export interface BestTimeResponse {
  best_window?: PostingTime | null;
  recommended_window?: PostingTime | null;
  recommendation?: PostingTime | null;
  slots?: BestTimeSlot[] | null;
  by_day?: BestTimeSlot[] | null;
  by_hour?: BestTimeSlot[] | null;
  [key: string]: unknown;
}

export interface SimilarResponse {
  topic?: string | null;
  hours?: number | null;
  stories?: SimilarStory[] | null;
  results?: SimilarStory[] | null;
  [key: string]: unknown;
}

export interface HealthResponse {
  status?: string | null;
  model_loaded?: boolean | null;
  model?: string | Record<string, unknown> | null;
  auth?: string | boolean | null;
  auth_enabled?: boolean | null;
  version?: string | null;
  [key: string]: unknown;
}
