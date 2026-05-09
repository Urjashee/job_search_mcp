from __future__ import annotations

import argparse
from typing import Sequence

from .models import AppInfo
from .services.jobs import JobRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-search-mcp",
        description="Job Search MCP command-line interface.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="info",
        choices=("info", "demo", "mcp"),
        help="Command to run.",
    )
    return parser


def run_info() -> None:
    info = AppInfo()
    print(info.summary())


def run_demo() -> None:
    repository = JobRepository()
    repository.seed_demo_jobs()
    print("Seeded demo jobs:")
    for job in repository.list_jobs():
        print(f"- {job.title} at {job.company} [{job.location}]")


def run_mcp() -> None:
    from .mcp_server import run_mcp_server

    run_mcp_server()


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "info":
        run_info()
    elif args.command == "demo":
        run_demo()
    elif args.command == "mcp":
        run_mcp()


if __name__ == "__main__":
    main()
