/**
 * TypeScript types for unified human analysis endpoint
 */

export type HumanAnalyzeMode = "url" | "image" | "text";
export type HumanAnalyzeGoal = "leads" | "sales" | "booking" | "contact" | "subscribe" | "other";
export type HumanAnalyzeLocale = "fa" | "en" | "tr";

export interface HumanAnalyzeIssue {
  title?: string;
  problem?: string;
  why_it_hurts?: string;
  location?: string;
  fix?: string;
  severity?: string;
  id?: string;
}

export interface HumanAnalyzeQuickWin {
  action: string;
  where?: {
    section?: string;
    selector?: string;
  };
  reason?: string;
}

export interface HumanAnalyzeSummary {
  url?: string | null;
  goal: string;
  locale: string;
  headlines_count?: number;
  ctas_count?: number;
  issues_count?: number;
  quick_wins_count?: number;
  message?: string;
}

export interface HumanAnalyzeResponse {
  status: "ok" | "error";
  mode: HumanAnalyzeMode;
  goal: string;
  human_report: string;
  page_map?: any;
  summary?: HumanAnalyzeSummary;
  issues?: HumanAnalyzeIssue[];
  quick_wins?: HumanAnalyzeQuickWin[];
  issues_count?: number;
  quick_wins_count?: number;
  screenshots?: any;
  debug?: any;
  // Legacy fields (may be present but deprecated)
  report?: string;
  findings?: {
    top_issues?: HumanAnalyzeIssue[];
    quick_wins?: HumanAnalyzeQuickWin[];
  };
  analysis_id?: string;
  page_type?: string;
  capture_info?: {
    screenshots?: any;
  };
}



