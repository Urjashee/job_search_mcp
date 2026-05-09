### Prerequisites

- Python 3.12 or newer
- `uv` if you want fast local environment management
- Copy `.env.example` to `.env` and fill in the values when you connect external services

### Install

From the project root:

```bash
uv sync
```

If you are not using `uv`, you can still run the project directly with Python once dependencies are added.

### Run

The current entrypoint is:

```bash
python main.py
```

If you are using `uv`:

```bash
uv run python main.py
```

To run the CLI entrypoint directly after installation:

```bash
uv run job-search-mcp
```

To see the seeded demo jobs:

```bash
uv run job-search-mcp demo
```

If `uv run` has cache permission issues on your machine, use:

```bash
python main.py demo
```

To start the API server during development:

```bash
uv run uvicorn job_search_mcp.api:app --reload
```

### Frontend Dev

From `frontend/`:

```bash
npm install
npm run dev
```
