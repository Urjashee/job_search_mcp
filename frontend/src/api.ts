export type JobPosting = {
  id: string;
  title: string;
  company: string;
  location: string;
  description: string;
  source: string;
  url?: string | null;
  remote: boolean;
  visa_sponsorship: boolean;
  created_at: string;
  tags: string[];
};

export type MatchedJob = {
  job: JobPosting;
  score: number;
  reasons: string[];
};

export type ResumeAnalysis = {
  extracted_skills: string[];
  summary: string;
  match_notes: string[];
};

export type IngestionSummary = {
  source: string;
  ingested: number;
};

export type SyncStatus = {
  enabled: boolean;
  interval_seconds: number;
  running: boolean;
  last_started_at: string | null;
  last_completed_at: string | null;
  last_results: IngestionSummary[];
};

export type AppInfo = {
  name: string;
  version: string;
  description: string;
  capabilities: string[];
};

export type SearchResponse = {
  items: MatchedJob[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type JobsResponse = {
  items: JobPosting[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }

  return (await response.json()) as T;
}

export async function getInfo() {
  return request<AppInfo>("/info");
}

export async function getJobs(page = 1, pageSize = 10) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  return request<JobsResponse>(`/jobs?${params.toString()}`);
}

export async function searchJobs(query: string, page = 1, pageSize = 10) {
  return request<SearchResponse>("/jobs/search", {
    method: "POST",
    body: JSON.stringify({ query, limit: pageSize, page, page_size: pageSize }),
  });
}

export async function analyzeResume(resumeText: string) {
  return request<{ item: ResumeAnalysis }>("/resumes/analyze", {
    method: "POST",
    body: JSON.stringify({ resume_text: resumeText }),
  });
}

export async function uploadResume(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return request<{ filename: string; extracted_text: string; analysis: ResumeAnalysis }>(
    "/resumes/upload",
    {
      method: "POST",
      body: formData,
    },
  );
}

export async function generateCoverLetter(payload: {
  resume_text: string;
  job_title: string;
  company: string;
}) {
  return request<{ item: string }>("/tools/cover-letter", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function importJobs(payload: {
  source: string;
  reference: string;
  company?: string;
  query?: string;
}) {
  return request<IngestionSummary>("/ingestion/import", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function ingestAll() {
  return request<IngestionSummary[]>("/ingestion/all", {
    method: "POST",
  });
}

export async function getSyncStatus() {
  return request<SyncStatus>("/ingestion/sync/status");
}

export async function runSyncNow() {
  return request<IngestionSummary[]>("/ingestion/sync/run", {
    method: "POST",
  });
}
