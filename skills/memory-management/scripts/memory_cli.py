#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pycozo[embedded]>=0.7",
#   "click>=8.1",
#   "tomli>=2.0; python_version<'3.11'",
# ]
# ///
"""Pyramid Memory CLI - Milestone 1 (storage + CLI)."""

import json

import click

VERSION = "0.1.0-m1"


@click.group()
def cli() -> None:
    """Pyramid Memory: graph + decision storage for AI-driven decomposition."""


@cli.command()
def version() -> None:
    """Print CLI version as JSON."""
    click.echo(
        json.dumps(
            {
                "ok": True,
                "data": {"version": VERSION},
                "warnings": [],
                "degraded": False,
            }
        )
    )


if __name__ == "__main__":
    cli()
