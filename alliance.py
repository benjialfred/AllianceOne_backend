#!/usr/bin/env python
import os
import sys

import typer

# Ensure the Django project is on the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Configure Typer app
app = typer.Typer(
    help="Alliance OS Command Line Interface",
    no_args_is_help=True
)

# We initialize our kernel abstractions here.
# In a real environment, this would be injected via the DI container.
from kernel.cli.services import DefaultCLIService  # noqa: E402

cli_service = DefaultCLIService()


@app.command()
def create_module(name: str) -> None:
    """Scaffold a new Alliance OS business module."""
    cli_service.create_module(name)


@app.command()
def publish(module_name: str) -> None:
    """Publish a module to the Alliance Marketplace."""
    cli_service.publish(module_name)


@app.command()
def doctor() -> None:
    """Run diagnostics on Alliance OS."""
    cli_service.doctor()


@app.command()
def migrate() -> None:
    """Run database migrations (wrapper around Django's migrate if needed, or independent)."""
    typer.echo("[Alliance CLI] Triggering kernel migrations...")
    os.system("python manage.py migrate")


@app.command()
def backup() -> None:
    """Trigger a full system backup."""
    typer.echo("[Alliance CLI] Initiating backup sequence...")


@app.command()
def tenant_create(name: str) -> None:
    """Create a new tenant organization."""
    typer.echo(f"[Alliance CLI] Creating new tenant: {name}")


@app.command()
def plugin_install(name: str) -> None:
    """Install a new plugin from the marketplace."""
    cli_service.install(name)


@app.command()
def license_activate(key: str) -> None:
    """Activate a platform license key."""
    typer.echo(f"[Alliance CLI] Activating license key: {key}")


if __name__ == "__main__":
    app()
