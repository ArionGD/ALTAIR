// Client for the ALTAIR FastAPI backend (see ../../../main.py).
// Override the target with PUBLIC_API_BASE in astro/.env if the backend
// isn't running on the default host/port.
export const API_BASE: string = import.meta.env.PUBLIC_API_BASE ?? "http://127.0.0.1:8001";

export interface StrikeRow {
  ticker: string;
  pe_ratio: number;
  debt_to_equity: number;
  revenue_growth: number;
  free_cash_flow: number;
  market: string;
  sector: string;
  bailout_probability: number;
  astra_strike_score: number;
  [key: string]: unknown;
}

export interface AuditStatus {
  in_progress: boolean;
  last_run: string | null;
}

export interface HealthCheck {
  status: string;
  engine: string;
  working_dir: string;
  data_ready: boolean;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText} — ${path}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: (): Promise<HealthCheck> => getJSON("/api/v1/health"),

  strikeList: (market?: string): Promise<StrikeRow[]> =>
    getJSON(`/api/v1/strike-list${market ? `?market=${encodeURIComponent(market)}` : ""}`),

  topTargets: (count: number, market?: string): Promise<StrikeRow[]> =>
    getJSON(`/api/v1/top-targets/${count}${market ? `?market=${encodeURIComponent(market)}` : ""}`),

  status: (): Promise<AuditStatus> => getJSON("/api/v1/status"),

  triggerAudit: async (): Promise<{ status: string; message: string }> => {
    const res = await fetch(`${API_BASE}/api/v1/audit`, { method: "POST" });
    return res.json();
  },

  // The V5 forensic-ticker endpoint depends on a file the current pipeline
  // doesn't generate (see project README, "Known backend issue"). Returns
  // null on any failure so callers can fall back to the strike-list row.
  tickerDetail: async (ticker: string): Promise<Record<string, unknown> | null> => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/forensic-ticker/${encodeURIComponent(ticker)}`);
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  },
};
