from __future__ import annotations


def render_index_html() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Job Search MCP</title>
  <style>
    :root {
      --bg: #0b1020;
      --panel: #121935;
      --panel-2: #172044;
      --text: #ecf2ff;
      --muted: #a9b5d1;
      --accent: #6ee7b7;
      --accent-2: #60a5fa;
      --border: rgba(255, 255, 255, 0.08);
    }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(96,165,250,0.18), transparent 30%),
        radial-gradient(circle at top right, rgba(110,231,183,0.16), transparent 24%),
        var(--bg);
      color: var(--text);
    }
    .wrap { max-width: 1180px; margin: 0 auto; padding: 32px 20px 60px; }
    .hero { display: grid; gap: 14px; padding: 28px; border: 1px solid var(--border); background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02)); border-radius: 24px; }
    .eyebrow { color: var(--accent); text-transform: uppercase; letter-spacing: 0.12em; font-size: 12px; }
    h1 { margin: 0; font-size: clamp(32px, 5vw, 56px); line-height: 1.02; }
    .lead { max-width: 72ch; color: var(--muted); font-size: 17px; line-height: 1.6; }
    .grid { display: grid; grid-template-columns: 1.05fr 0.95fr; gap: 18px; margin-top: 18px; }
    .card { background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-radius: 20px; padding: 18px; }
    .card h2 { margin: 0 0 10px; font-size: 18px; }
    .controls { display: flex; gap: 10px; flex-wrap: wrap; }
    input, textarea, button {
      border-radius: 12px;
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.04);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
    }
    input, textarea { width: 100%; box-sizing: border-box; }
    textarea { min-height: 120px; resize: vertical; }
    button { cursor: pointer; background: linear-gradient(135deg, var(--accent-2), var(--accent)); color: #08111d; font-weight: 700; }
    .jobs { display: grid; gap: 12px; margin-top: 12px; }
    .job { padding: 14px; border-radius: 14px; background: var(--panel); border: 1px solid var(--border); }
    .job-title { font-weight: 700; margin-bottom: 4px; }
    .job-meta { color: var(--muted); font-size: 14px; }
    .pill { display: inline-flex; align-items: center; gap: 6px; margin-right: 8px; padding: 5px 10px; border-radius: 999px; background: rgba(96,165,250,0.14); color: #cfe4ff; font-size: 12px; }
    pre { white-space: pre-wrap; word-break: break-word; background: var(--panel-2); padding: 14px; border-radius: 14px; border: 1px solid var(--border); color: var(--text); }
    .stack { display: grid; gap: 12px; }
    @media (max-width: 920px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="eyebrow">Job Search MCP</div>
      <h1>Agentic job search, resume matching, and source ingestion.</h1>
      <p class="lead">This prototype combines job ingestion, semantic ranking, resume parsing, and an MCP-style tool layer. It now persists jobs locally and has a real browser UI for searching and uploading resumes.</p>
    </section>

    <div class="grid">
      <section class="card">
        <h2>Search jobs</h2>
        <div class="stack">
          <input id="query" placeholder="e.g. remote Python RAG engineer" value="remote AI engineer" />
          <div class="controls">
            <button onclick="searchJobs()">Search</button>
            <button onclick="ingestAll()">Refresh demo sources</button>
          </div>
        </div>
        <div id="jobs" class="jobs"></div>
      </section>

      <section class="card">
        <h2>Upload resume</h2>
        <div class="stack">
          <input id="resumeFile" type="file" />
          <textarea id="resumeText" placeholder="Or paste resume text here"></textarea>
          <div class="controls">
            <button onclick="uploadResume()">Analyze resume</button>
            <button onclick="generateCoverLetter()">Generate cover letter</button>
          </div>
          <pre id="output">Results will appear here.</pre>
        </div>
      </section>
    </div>
  </div>

  <script>
    async function searchJobs() {
      const query = document.getElementById("query").value;
      const response = await fetch("/jobs/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, limit: 10 }),
      });
      const data = await response.json();
      const jobs = data.items || [];
      const container = document.getElementById("jobs");
      container.innerHTML = jobs.length ? jobs.map(renderJob).join("") : "<div class='job'>No matches yet.</div>";
    }

    function renderJob(item) {
      const job = item.job;
      const tags = (job.tags || []).map(tag => `<span class="pill">${tag}</span>`).join("");
      return `
        <div class="job">
          <div class="job-title">${job.title} · ${job.company}</div>
          <div class="job-meta">${job.location} · score ${item.score} · source ${job.source}</div>
          <p>${job.description || ""}</p>
          <div>${tags}</div>
        </div>`;
    }

    async function uploadResume() {
      const file = document.getElementById("resumeFile").files[0];
      const text = document.getElementById("resumeText").value;
      const output = document.getElementById("output");

      if (file) {
        const form = new FormData();
        form.append("file", file);
        const response = await fetch("/resumes/upload", { method: "POST", body: form });
        output.textContent = JSON.stringify(await response.json(), null, 2);
        return;
      }

      const response = await fetch("/resumes/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume_text: text }),
      });
      output.textContent = JSON.stringify(await response.json(), null, 2);
    }

    async function generateCoverLetter() {
      const text = document.getElementById("resumeText").value;
      const response = await fetch("/tools/cover-letter", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_text: text,
          job_title: "AI Engineer",
          company: "Northstar Labs",
        }),
      });
      const data = await response.json();
      document.getElementById("output").textContent = data.item;
    }

    async function ingestAll() {
      await fetch("/ingestion/all", { method: "POST" });
      await searchJobs();
    }

    searchJobs();
  </script>
</body>
</html>
    """
