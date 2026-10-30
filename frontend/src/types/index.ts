/**
 * src/types/index.ts — Shared types matching backend response shapes.
 * No `any` types — fully typed.
 */

export interface Source {
  title?: string;
  url?: string;
  href?: string;
  domain?: string;
  tier?: string;
  stance?: string;
  source?: string;
  relevance_score?: number;
}

export interface AgentTraceStep {
  name: string;
  args: Record<string, unknown>;
  result?: string;
  success?: boolean;
  error?: string;
}

export interface Verification {
  id: number;
  claim_text: string;
  verdict: string; // "True" | "False" | "Misleading" | "Unverified"
  confidence: number; // 0-100
  reasoning: string;
  sources: Source[];
  agent_trace: AgentTraceStep[];
  created_at: string;
}

export interface VerifyRequest {
  claim: string;
}

export interface VerifyResponse extends Verification {
  // Same shape, returned by POST /verify
}

export interface HistoryResponse {
  results: Verification[];
  count: number;
}

export interface SearchResponse {
  results: Verification[];
  count: number;
  query: string;
}

export type VerdictType = "True" | "False" | "Misleading" | "Unverified";
