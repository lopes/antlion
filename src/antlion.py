import os
import shutil
import sys
from pathlib import Path

import anthropic

from src.cli import CliArgs, CliError, parse_args
from src.generator import generate_all
from src.manifest import manifest_exists, read_manifest, write_manifest
from src.models import (
    EXIT_API_ERROR,
    EXIT_CLI_ERROR,
    EXIT_ENV_ERROR,
    EXIT_PARTIAL,
    EXIT_PLANNING_ERROR,
    EXIT_SUCCESS,
    Manifest,
    OperationParameters,
)
from src.planner import PlanningError, plan_campaign
from src.resume import ResumeAction, determine_resume_action


def _build_operation_parameters(cli: CliArgs) -> OperationParameters:
    return OperationParameters(
        base_dir=cli.base_dir,
        num_files=cli.num_files,
        formats=cli.formats,
        teams=cli.teams,
        company=cli.company,
        file_content=cli.file_content,
        model=cli.model,
        passwords=cli.passwords,
    )


def _print_plan(manifest: Manifest) -> None:
    print(f"Operation: {manifest.operation}")
    print(f"Files: {len(manifest.files)}")
    for entry in manifest.files:
        print(f"  {entry.path} ({entry.format}) — {entry.summary}")


def _prompt_user_resume() -> bool:
    response = input("Existing operation found. Resume? (y/n): ").strip().lower()
    return response == "y"


def run(argv: list[str]) -> int:
    result = parse_args(argv)
    if isinstance(result, CliError):
        print(f"Error: {result.message}", file=sys.stderr)
        return EXIT_CLI_ERROR

    cli = result

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable is not set", file=sys.stderr)
        return EXIT_ENV_ERROR

    client = anthropic.Anthropic()
    operation_dir = Path(cli.base_dir) / cli.operation
    action = determine_resume_action(
        manifest_exists=manifest_exists(operation_dir),
        resume_flag=cli.resume,
    )

    manifest: Manifest | None = None
    is_resume = False

    if action == ResumeAction.RESUME:
        manifest = read_manifest(operation_dir)
        is_resume = True
        print(f"Resuming operation '{cli.operation}'")
    elif action == ResumeAction.PROMPT:
        if _prompt_user_resume():
            manifest = read_manifest(operation_dir)
            is_resume = True
        else:
            shutil.rmtree(operation_dir)
    elif action == ResumeAction.FRESH_WITH_MESSAGE:
        print(f"New operation '{cli.operation}'; starting generation")

    if manifest is None:
        params = _build_operation_parameters(cli)
        try:
            plan = plan_campaign(client, params)
        except PlanningError as e:
            print(f"Error: {e}", file=sys.stderr)
            return EXIT_API_ERROR if e.is_api_error else EXIT_PLANNING_ERROR

        manifest = Manifest(
            operation=cli.operation,
            parameters=params,
            files=plan.files,
        )
        operation_dir.mkdir(parents=True, exist_ok=True)
        write_manifest(manifest, operation_dir)

    if cli.dry_run:
        _print_plan(manifest)
        return EXIT_SUCCESS

    try:
        failures = generate_all(client, manifest, operation_dir, resume=is_resume)
    except anthropic.APIError as e:
        print(f"Error: {e}", file=sys.stderr)
        return EXIT_API_ERROR

    if failures > 0:
        print(f"{failures} file(s) failed to generate", file=sys.stderr)
        return EXIT_PARTIAL

    return EXIT_SUCCESS


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
