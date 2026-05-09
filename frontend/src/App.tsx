import { useEffect, useMemo, useState } from "react";
import {
  analyzeResume,
  AppInfo,
  generateCoverLetter,
  getInfo,
  getJobs,
  getSyncStatus,
  importJobs,
  ingestAll,
  runSyncNow,
  searchJobs,
  uploadResume,
  type JobsResponse,
  type JobPosting,
  type MatchedJob,
  type ResumeAnalysis,
  type SyncStatus,
} from "./api";

const sourceOptions = [
  { value: "greenhouse", label: "Greenhouse" },
  { value: "lever", label: "Lever" },
  { value: "jsearch", label: "Jsearch" },
  { value: "adzuna", label: "Adzuna" },
];

function formatTime(value: string | null) {
  if (!value) return "never";
  return new Date(value).toLocaleString();
}

function App() {
  const [info, setInfo] = useState<AppInfo | null>(null);
  const [jobsPage, setJobsPage] = useState<JobsResponse | null>(null);
  const [searchPage, setSearchPage] = useState<{
    items: MatchedJob[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  } | null>(null);
  const [activeView, setActiveView] = useState<"jobs" | "search">("jobs");
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [query, setQuery] = useState("remote AI engineer");
  const [resumeText, setResumeText] = useState("");
  const [analysis, setAnalysis] = useState<ResumeAnalysis | null>(null);
  const [coverLetter, setCoverLetter] = useState("");
  const [status, setStatus] = useState<string>("Loading...");
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importSource, setImportSource] = useState("greenhouse");
  const [importReference, setImportReference] = useState("example-company");
  const [importCompany, setImportCompany] = useState("Example Company");
  const [importQuery, setImportQuery] = useState("software engineer");
  const [importCount, setImportCount] = useState<number | null>(null);
  const [syncNowCount, setSyncNowCount] = useState<number | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const pageSize = 6;

  const selectedJob = useMemo(
    () =>
      (activeView === "search"
        ? searchPage?.items.find((item) => item.job.id === selectedJobId)?.job
        : jobsPage?.items.find((job) => job.id === selectedJobId)) ??
      (activeView === "search"
        ? searchPage?.items[0]?.job ?? jobsPage?.items[0] ?? null
        : jobsPage?.items[0] ?? searchPage?.items[0]?.job ?? null),
    [activeView, jobsPage, searchPage, selectedJobId],
  );

  useEffect(() => {
    void bootstrap();
  }, []);

  useEffect(() => {
    const fallbackJob = activeView === "search"
      ? searchPage?.items[0]?.job
      : jobsPage?.items[0] ?? null;

    if (!selectedJobId && fallbackJob) {
      setSelectedJobId(fallbackJob.id);
    }
  }, [activeView, jobsPage, searchPage, selectedJobId]);

  async function bootstrap() {
    setIsBusy(true);
    setError(null);
    try {
      const [appInfo, jobList, sync] = await Promise.all([
        getInfo(),
        getJobs(1, pageSize),
        getSyncStatus(),
      ]);
      setInfo(appInfo);
      setJobsPage(jobList);
      setSyncStatus(sync);
      setActiveView("jobs");
      setStatus(`Loaded ${jobList.total} jobs`);
      if (jobList.items.length > 0) {
        setSelectedJobId(jobList.items[0].id);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Failed to load app");
      setStatus("Load failed");
    } finally {
      setIsBusy(false);
    }
  }

  async function loadJobsPage(page: number) {
    const data = await getJobs(page, pageSize);
    setJobsPage(data);
    setActiveView("jobs");
    if (data.items.length > 0) {
      setSelectedJobId(data.items[0].id);
    }
  }

  async function loadSearchPage(page: number) {
    const response = await searchJobs(query, page, pageSize);
    setSearchPage(response);
    setActiveView("search");
    if (response.items.length > 0) {
      setSelectedJobId(response.items[0].job.id);
    }
  }

  async function handleSearch() {
    setIsBusy(true);
    setError(null);
    try {
      await loadSearchPage(1);
      setStatus(`Found search results for "${query}"`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Search failed");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleAnalyzeResume() {
    setIsBusy(true);
    setError(null);
    try {
      if (selectedFile) {
        const uploaded = await uploadResume(selectedFile);
        setAnalysis(uploaded.analysis);
        setResumeText(uploaded.extracted_text);
        setCoverLetter("");
        setStatus(`Parsed ${uploaded.filename}`);
      } else {
        const analyzed = await analyzeResume(resumeText);
        setAnalysis(analyzed.item);
        setCoverLetter("");
        setStatus("Resume analyzed");
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Resume analysis failed");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleGenerateCoverLetter() {
    const job = selectedJob;
    if (!job) return;

    setIsBusy(true);
    setError(null);
    try {
      const result = await generateCoverLetter({
        resume_text: resumeText,
        job_title: job.title,
        company: job.company,
      });
      setCoverLetter(result.item);
      setStatus("Cover letter generated");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Cover letter generation failed");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleImport() {
    setIsBusy(true);
    setError(null);
    try {
      const result = await importJobs({
        source: importSource,
        reference: importReference,
        company: importCompany || undefined,
        query: importQuery || undefined,
      });
      setImportCount(result.ingested);
      await bootstrap();
      if (activeView === "search") {
        await loadSearchPage(1);
      }
      setStatus(`Imported ${result.ingested} jobs from ${importSource}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Import failed");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleRefreshAll() {
    setIsBusy(true);
    setError(null);
    try {
      const result = await ingestAll();
      setImportCount(result.reduce((total, item) => total + item.ingested, 0));
      await bootstrap();
      if (activeView === "search") {
        await loadSearchPage(1);
      }
      setStatus("Refreshed all configured sources");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Refresh failed");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleSyncNow() {
    setIsBusy(true);
    setError(null);
    try {
      const result = await runSyncNow();
      setSyncNowCount(result.reduce((total, item) => total + item.ingested, 0));
      const sync = await getSyncStatus();
      setSyncStatus(sync);
      await bootstrap();
      if (activeView === "search") {
        await loadSearchPage(1);
      }
      setStatus("Background sync completed");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Sync failed");
    } finally {
      setIsBusy(false);
    }
  }

  async function handlePageChange(direction: "prev" | "next") {
    const current = activeView === "search" ? searchPage : jobsPage;
    if (!current) return;
    const nextPage = direction === "next" ? current.page + 1 : current.page - 1;
    if (nextPage < 1 || nextPage > current.total_pages) return;

    setIsBusy(true);
    setError(null);
    try {
      if (activeView === "search") {
        await loadSearchPage(nextPage);
      } else {
        await loadJobsPage(nextPage);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Pagination failed");
    } finally {
      setIsBusy(false);
    }
  }

  const metrics = [
    { label: "Jobs", value: jobsPage?.total ?? 0 },
    { label: "Results", value: activeView === "search" ? searchPage?.total ?? 0 : jobsPage?.total ?? 0 },
    { label: "Remote", value: (jobsPage?.items ?? []).filter((job) => job.remote).length },
    { label: "Visa roles", value: (jobsPage?.items ?? []).filter((job) => job.visa_sponsorship).length },
  ];

  const displayedResults = activeView === "search" ? searchPage : jobsPage;
  const displayedItems =
    activeView === "search"
      ? searchPage?.items.map((item) => item.job) ?? []
      : jobsPage?.items ?? [];

  return (
    <div className="app-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />

      <main className="layout">
        <section className="hero">
          <div className="hero-copy">
            <div className="eyebrow">Job Search MCP</div>
            <h1>Agentic job search with ingestion, matching, and resume intelligence.</h1>
            <p>
              Search real sources, import Greenhouse or Lever boards, upload a resume,
              and generate tailored cover letters from one workspace.
            </p>
          </div>

          <div className="hero-meta">
            <div className="status-chip">{status}</div>
            <div className="info-row">
              <span>Backend</span>
              <strong>{info?.name ?? "Loading..."}</strong>
            </div>
            <div className="info-row">
              <span>Version</span>
              <strong>{info?.version ?? "0.1.0"}</strong>
            </div>
            <div className="info-row">
              <span>Sync</span>
              <strong>{syncStatus?.enabled ? "Enabled" : "Disabled"}</strong>
            </div>
          </div>
        </section>

        <section className="metrics">
          {metrics.map((metric) => (
            <article key={metric.label} className="metric-card">
              <span>{metric.label}</span>
              <strong>{metric.value}</strong>
            </article>
          ))}
        </section>

        <section className="content-grid">
          <div className="left-column">
            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>Search jobs</h2>
                  <p>Keyword plus vector ranking over the stored job set.</p>
                </div>
                <button disabled={isBusy} onClick={handleSearch}>
                  Search
                </button>
              </div>

              <div className="control-stack">
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="remote Python RAG engineer"
                />
              </div>

              <div className="panel-footer">
                <span>
                  {displayedResults
                    ? `Page ${displayedResults.page} of ${displayedResults.total_pages} · ${displayedResults.total} total`
                    : "No results loaded"}
                </span>
                <div className="panel-actions">
                  <button
                    disabled={isBusy || !displayedResults || displayedResults.page <= 1}
                    onClick={() => handlePageChange("prev")}
                  >
                    Previous
                  </button>
                  <button
                    disabled={
                      isBusy ||
                      !displayedResults ||
                      displayedResults.page >= displayedResults.total_pages
                    }
                    onClick={() => handlePageChange("next")}
                  >
                    Next
                  </button>
                </div>
              </div>

              <div className="job-list">
                {activeView === "search"
                  ? searchPage?.items.map((item) => (
                      <button
                        key={item.job.id}
                        className={`job-card ${selectedJobId === item.job.id ? "selected" : ""}`}
                        onClick={() => setSelectedJobId(item.job.id)}
                      >
                        <div className="job-head">
                          <strong>
                            {item.job.title} · {item.job.company}
                          </strong>
                          <span>{item.score.toFixed(2)}</span>
                        </div>
                        <p>{item.job.location}</p>
                        <div className="tag-row">
                          {item.job.tags.map((tag) => (
                            <span key={tag} className="tag">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </button>
                    ))
                  : jobsPage?.items.map((job) => (
                      <button
                        key={job.id}
                        className={`job-card ${selectedJobId === job.id ? "selected" : ""}`}
                        onClick={() => setSelectedJobId(job.id)}
                      >
                        <div className="job-head">
                          <strong>
                            {job.title} · {job.company}
                          </strong>
                          <span>saved</span>
                        </div>
                        <p>{job.location}</p>
                        <div className="tag-row">
                          {job.tags.map((tag) => (
                            <span key={tag} className="tag">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </button>
                    ))}
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>Job details</h2>
                  <p>Signals used for ranking and matching.</p>
                </div>
              </div>

              {selectedJob ? (
                <div className="details">
                  <div className="details-title">
                    <h3>{selectedJob.title}</h3>
                    <span>{selectedJob.company}</span>
                  </div>
                  <p>{selectedJob.description}</p>
                  <div className="detail-grid">
                    <div>
                      <span>Location</span>
                      <strong>{selectedJob.location}</strong>
                    </div>
                    <div>
                      <span>Source</span>
                      <strong>{selectedJob.source}</strong>
                    </div>
                    <div>
                      <span>Remote</span>
                      <strong>{selectedJob.remote ? "Yes" : "No"}</strong>
                    </div>
                    <div>
                      <span>Visa</span>
                      <strong>{selectedJob.visa_sponsorship ? "Yes" : "No"}</strong>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="muted">No job selected yet.</p>
              )}
            </div>
          </div>

          <div className="right-column">
            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>Resume analysis</h2>
                  <p>Upload a file or paste resume text.</p>
                </div>
                <button disabled={isBusy} onClick={handleAnalyzeResume}>
                  Analyze
                </button>
              </div>

              <div className="control-stack">
                <input
                  type="file"
                  accept=".txt,.pdf,.docx"
                  onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                />
                <textarea
                  value={resumeText}
                  onChange={(event) => setResumeText(event.target.value)}
                  placeholder="Paste a resume or candidate summary here."
                />
              </div>

              {analysis ? (
                <div className="analysis-box">
                  <div className="tag-row">
                    {analysis.extracted_skills.map((skill) => (
                      <span key={skill} className="tag accent">
                        {skill}
                      </span>
                    ))}
                  </div>
                  <p>{analysis.summary}</p>
                  <ul>
                    {analysis.match_notes.map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="muted">No analysis yet.</p>
              )}
            </div>

            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>Cover letter</h2>
                  <p>Generated locally or via OpenAI if configured.</p>
                </div>
                <button disabled={isBusy || !selectedJob} onClick={handleGenerateCoverLetter}>
                  Generate
                </button>
              </div>
              <pre className="output">{coverLetter || "Cover letter output appears here."}</pre>
            </div>

            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>Import source</h2>
                  <p>Import Greenhouse, Lever, Jsearch, or Adzuna jobs.</p>
                </div>
                <div className="panel-actions">
                  <button disabled={isBusy} onClick={handleRefreshAll}>
                    Refresh all
                  </button>
                  <button disabled={isBusy} onClick={handleSyncNow}>
                    Sync now
                  </button>
                </div>
              </div>

              <div className="control-grid">
                <label>
                  Source
                  <select value={importSource} onChange={(event) => setImportSource(event.target.value)}>
                    {sourceOptions.map((source) => (
                      <option key={source.value} value={source.value}>
                        {source.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Reference
                  <input
                    value={importReference}
                    onChange={(event) => setImportReference(event.target.value)}
                    placeholder="example-company"
                  />
                </label>
                <label>
                  Company
                  <input
                    value={importCompany}
                    onChange={(event) => setImportCompany(event.target.value)}
                    placeholder="Optional company name"
                  />
                </label>
                <label>
                  Query
                  <input
                    value={importQuery}
                    onChange={(event) => setImportQuery(event.target.value)}
                    placeholder="software engineer"
                  />
                </label>
              </div>

              <div className="panel-footer">
                <button disabled={isBusy} onClick={handleImport}>
                  Import
                </button>
                <span>
                  {importCount !== null ? `Imported ${importCount} jobs` : "No import run yet"}
                </span>
                <span>
                  {syncNowCount !== null ? `Sync added ${syncNowCount}` : "Sync idle"}
                </span>
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>Sync status</h2>
                  <p>Background refresh state.</p>
                </div>
              </div>

              <div className="detail-grid">
                <div>
                  <span>Enabled</span>
                  <strong>{syncStatus?.enabled ? "Yes" : "No"}</strong>
                </div>
                <div>
                  <span>Interval</span>
                  <strong>{syncStatus ? `${syncStatus.interval_seconds}s` : "n/a"}</strong>
                </div>
                <div>
                  <span>Running</span>
                  <strong>{syncStatus?.running ? "Yes" : "No"}</strong>
                </div>
                <div>
                  <span>Last run</span>
                  <strong>{formatTime(syncStatus?.last_completed_at ?? null)}</strong>
                </div>
              </div>

              <div className="sync-results">
                {syncStatus?.last_results?.length ? (
                  syncStatus.last_results.map((item) => (
                    <div key={item.source} className="sync-row">
                      <span>{item.source}</span>
                      <strong>{item.ingested}</strong>
                    </div>
                  ))
                ) : (
                  <p className="muted">No sync results yet.</p>
                )}
              </div>
            </div>
          </div>
        </section>

        {error ? <div className="error-banner">{error}</div> : null}
      </main>
    </div>
  );
}

export default App;
