/**
 * src/api/client.ts — Typed fetch wrapper for all 5 backend endpoints.
 */

import type { Verification, VerifyRequest, VerifyResponse, HistoryResponse, SearchResponse } from "../types";

const BASE_URL = "http://localhost:8000";

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...((options?.headers as Record<string, string>) || {}),
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API error ${response.status}: ${errorText}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  verify: async (req: VerifyRequest): Promise<VerifyResponse> => {
    return fetchJSON<VerifyResponse>(`${BASE_URL}/verify`, {
      method: "POST",
      body: JSON.stringify(req),
    });
  },

  getHistory: async (limit = 50, offset = 0): Promise<HistoryResponse> => {
    return fetchJSON<HistoryResponse>(
      `${BASE_URL}/history?limit=${limit}&offset=${offset}`
    );
  },

  getVerification: async (id: number): Promise<Verification> => {
    return fetchJSON<Verification>(`${BASE_URL}/history/${id}`);
  },

  searchHistory: async (q: string, limit = 20): Promise<SearchResponse> => {
    return fetchJSON<SearchResponse>(
      `${BASE_URL}/history/search?q=${encodeURIComponent(q)}&limit=${limit}`
    );
  },

  deleteVerification: async (id: number): Promise<{ deleted: boolean; id: number }> => {
    return fetchJSON<{ deleted: boolean; id: number }>(`${BASE_URL}/history/${id}`, {
      method: "DELETE",
    });
  },
};
