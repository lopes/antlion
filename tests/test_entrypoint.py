from pathlib import Path
from unittest.mock import MagicMock, patch

import anthropic
import pytest
from anthropic.types import TextBlock, ToolUseBlock

from antlion import run
from antlion.models import (
    EXIT_API_ERROR,
    EXIT_CLI_ERROR,
    EXIT_ENV_ERROR,
    EXIT_PARTIAL,
    EXIT_PLANNING_ERROR,
    EXIT_SUCCESS,
)


def test_bad_cli_args_returns_exit_code_1():
    result = run(["--num-files", "abc"])
    assert result == EXIT_CLI_ERROR


def test_missing_api_key_returns_exit_code_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = run(
        [
            "--base-dir",
            str(tmp_path),
            "--operation",
            "op1",
            "--num-files",
            "1",
            "--formats",
            "md",
            "--teams",
            "it",
            "--company",
            "Acme",
            "--file-content",
            "docs",
        ]
    )
    assert result == EXIT_ENV_ERROR


def _valid_argv(tmp_path: Path) -> list[str]:
    return [
        "--base-dir",
        str(tmp_path),
        "--operation",
        "op_test",
        "--num-files",
        "2",
        "--formats",
        "md,conf",
        "--teams",
        "it",
        "--company",
        "Acme",
        "--file-content",
        "docs",
    ]


def _make_plan_response(files: list[dict[str, str]]) -> MagicMock:
    block = ToolUseBlock(
        id="toolu_test",
        type="tool_use",
        name="campaign_plan",
        input={"files": files},
    )
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "tool_use"
    return response


def _make_content_response(text: str) -> MagicMock:
    block = TextBlock(type="text", text=text)
    response = MagicMock()
    response.content = [block]
    return response


def test_successful_run_returns_exit_0(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    plan_files = [
        {"path": "it/notes.md", "format": "md", "summary": "Notes"},
        {"path": "it/app.conf", "format": "conf", "summary": "Config"},
    ]

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _make_plan_response(plan_files),
        _make_content_response("# Notes\nSome content"),
        _make_content_response("[main]\nkey=value"),
    ]

    with patch("antlion.__main__.anthropic.Anthropic", return_value=mock_client):
        result = run(_valid_argv(tmp_path))

    assert result == EXIT_SUCCESS
    op_dir = tmp_path / "op_test"
    assert (op_dir / "MANIFEST.json").exists()
    assert (op_dir / "it" / "notes.md").exists()
    assert (op_dir / "it" / "app.conf").exists()


def test_partial_completion_returns_exit_4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    plan_files = [
        {"path": "a.md", "format": "md", "summary": "A"},
        {"path": "b.md", "format": "md", "summary": "B"},
    ]

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _make_plan_response(plan_files),
        _make_content_response("Content A"),
        Exception("Generation failed"),
    ]

    with patch("antlion.__main__.anthropic.Anthropic", return_value=mock_client):
        result = run(_valid_argv(tmp_path))

    assert result == EXIT_PARTIAL


def test_planning_error_returns_exit_5(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_client = MagicMock()
    response = MagicMock()
    response.content = []
    response.stop_reason = "end_turn"
    mock_client.messages.create.return_value = response

    with patch("antlion.__main__.anthropic.Anthropic", return_value=mock_client):
        result = run(_valid_argv(tmp_path))

    assert result == EXIT_PLANNING_ERROR


def test_api_error_during_planning_returns_exit_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = anthropic.APIError(
        message="rate limited",
        request=MagicMock(),
        body=None,
    )

    with patch("antlion.__main__.anthropic.Anthropic", return_value=mock_client):
        result = run(_valid_argv(tmp_path))

    assert result == EXIT_API_ERROR
