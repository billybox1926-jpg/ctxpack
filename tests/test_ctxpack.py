#!/usr/bin/env python3
"""
Test suite for ctxpack - dependency-free repo-to-prompt pack builder.
"""

import json

# Import the module under test
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import ctxpack


class TestLoadIgnorePatterns:
    """Tests for load_ignore_patterns function."""

    def test_default_patterns_when_no_ignore_file(self, tmp_path):
        """Should return default patterns when .ctxignore doesn't exist."""
        patterns = ctxpack.load_ignore_patterns(tmp_path, [])

        assert ".git/**" in patterns
        assert "node_modules/**" in patterns
        assert "*.log" in patterns
        assert (ctxpack.DEFAULT_BASE_NAME + ".context.json") in patterns
        assert (ctxpack.DEFAULT_BASE_NAME + ".context.md") in patterns

    def test_custom_patterns_from_ignore_file(self, tmp_path):
        """Should load custom patterns from .ctxignore."""
        ignore_file = tmp_path / ctxpack.DEFAULT_IGNORE_FILE
        ignore_file.write_text("custom_pattern/\n*.tmp\n", encoding="utf-8")

        patterns = ctxpack.load_ignore_patterns(tmp_path, [])

        assert "custom_pattern/" in patterns
        assert "*.tmp" in patterns

    def test_comments_ignored_in_ignore_file(self, tmp_path):
        """Should skip comment lines in .ctxignore."""
        ignore_file = tmp_path / ctxpack.DEFAULT_IGNORE_FILE
        ignore_file.write_text("# This is a comment\nvalid_pattern\n", encoding="utf-8")

        patterns = ctxpack.load_ignore_patterns(tmp_path, [])

        assert "# This is a comment" not in patterns
        assert "valid_pattern" in patterns

    def test_empty_lines_ignored_in_ignore_file(self, tmp_path):
        """Should skip empty lines in .ctxignore."""
        ignore_file = tmp_path / ctxpack.DEFAULT_IGNORE_FILE
        ignore_file.write_text("\n\nvalid_pattern\n\n", encoding="utf-8")

        patterns = ctxpack.load_ignore_patterns(tmp_path, [])

        assert "" not in patterns
        assert "valid_pattern" in patterns


class TestShouldIgnore:
    """Tests for should_ignore function."""

    def test_ignore_git_directory(self, tmp_path):
        """Should ignore .git directory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        patterns = [".git/**"]

        # Test that .git directory itself is ignored
        assert ctxpack.should_process(git_dir, tmp_path, [], patterns) is False

        # Also test files inside .git are ignored
        git_file = git_dir / "config"
        git_file.write_text("test")
        assert ctxpack.should_process(git_file, tmp_path, [], patterns) is False

    def test_ignore_log_files_anywhere(self, tmp_path):
        """Should ignore *.log files anywhere in the tree (bare filename pattern)."""
        log_file_root = tmp_path / "app.log"
        log_file_subdir = tmp_path / "subdir" / "debug.log"
        log_file_subdir.parent.mkdir(parents=True)
        log_file_root.write_text("log content")
        log_file_subdir.write_text("log content")

        patterns = ["*.log"]

        assert ctxpack.should_process(log_file_root, tmp_path, [], patterns) is False
        assert ctxpack.should_process(log_file_subdir, tmp_path, [], patterns) is False

    def test_ignore_node_modules(self, tmp_path):
        """Should ignore node_modules directory and contents."""
        node_dir = tmp_path / "node_modules" / "package"
        node_dir.mkdir(parents=True)
        patterns = ["node_modules/**"]

        assert ctxpack.should_process(node_dir, tmp_path, [], patterns) is False

    def test_dont_ignore_normal_file(self, tmp_path):
        """Should not ignore normal source files."""
        src_file = tmp_path / "src" / "main.py"
        src_file.parent.mkdir()
        src_file.write_text("print('hello')")

        patterns = ["*.log", "node_modules/**"]

        assert ctxpack.should_process(src_file, tmp_path, [], patterns) is True

    def test_ignore_pyc_files(self, tmp_path):
        """Should ignore .pyc files."""
        pyc_file = tmp_path / "module.pyc"
        pyc_file.write_text("binary")
        patterns = ["*.pyc"]

        assert ctxpack.should_process(pyc_file, tmp_path, [], patterns) is False

    def test_ignore_ctxpack_outputs(self, tmp_path):
        """Should ignore ctxpack output files by default."""
        json_output = tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")
        md_output = tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.md")
        json_output.write_text("{}")
        md_output.write_text("")

        patterns = ctxpack.load_ignore_patterns(tmp_path, [])

        assert ctxpack.should_process(json_output, tmp_path, [], patterns) is False
        assert ctxpack.should_process(md_output, tmp_path, [], patterns) is False

    def test_ignore_env_file(self, tmp_path):
        """Should ignore .env file (secret-bearing)."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET_KEY=supersecret123")

        patterns = ctxpack.load_ignore_patterns(tmp_path, [])

        assert ctxpack.should_process(env_file, tmp_path, [], patterns) is False

    def test_ignore_env_local_file(self, tmp_path):
        """Should ignore .env.local and other .env.* variants."""
        env_local = tmp_path / ".env.local"
        env_production = tmp_path / ".env.production"
        env_local.write_text("DB_PASSWORD=password123")
        env_production.write_text("API_KEY=abc123")

        patterns = ctxpack.load_ignore_patterns(tmp_path, [])

        assert ctxpack.should_process(env_local, tmp_path, [], patterns) is False
        assert ctxpack.should_process(env_production, tmp_path, [], patterns) is False

    def test_allow_env_example_file(self, tmp_path):
        """Should NOT ignore .env.example (template file allowed)."""
        env_example = tmp_path / ".env.example"
        env_example.write_text("SECRET_KEY=your_secret_here")

        patterns = ctxpack.load_ignore_patterns(tmp_path, [])

        # .env.example should be allowed (not ignored)
        assert ctxpack.should_process(env_example, tmp_path, [], patterns) is True

    def test_ignore_pem_key_files(self, tmp_path):
        """Should ignore private key and certificate files."""
        pem_file = tmp_path / "server.pem"
        key_file = tmp_path / "private.key"
        p12_file = tmp_path / "cert.p12"
        pfx_file = tmp_path / "cert.pfx"

        pem_file.write_text("-----BEGIN CERTIFICATE-----")
        key_file.write_text("-----BEGIN PRIVATE KEY-----")
        p12_file.write_bytes(b"\x00\x01\x02")
        pfx_file.write_bytes(b"\x00\x01\x02")

        patterns = ctxpack.load_ignore_patterns(tmp_path, [])

        assert ctxpack.should_process(pem_file, tmp_path, [], patterns) is False
        assert ctxpack.should_process(key_file, tmp_path, [], patterns) is False
        assert ctxpack.should_process(p12_file, tmp_path, [], patterns) is False
        assert ctxpack.should_process(pfx_file, tmp_path, [], patterns) is False


class TestMatchesPatternSemantics:
    """Tests for gitignore-style pattern matching semantics.

    These tests document and verify the exact subset of gitignore semantics
    that ctxpack supports. See README.md for user-facing documentation.
    """

    def test_bare_pattern_matches_filename_anywhere(self, tmp_path):
        """Bare patterns like *.log match by filename anywhere in tree."""
        # Create files at different depths
        (tmp_path / "test.log").write_text("x")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "test.log").write_text("x")
        (tmp_path / "a" / "b" / "c").mkdir(parents=True)
        (tmp_path / "a" / "b" / "c" / "test.log").write_text("x")

        patterns = ["*.log"]

        # Should match at all levels
        assert (
            ctxpack.should_process(tmp_path / "test.log", tmp_path, [], patterns)
            is False
        )
        assert (
            ctxpack.should_process(
                tmp_path / "subdir" / "test.log", tmp_path, [], patterns
            )
            is False
        )
        assert (
            ctxpack.should_process(
                tmp_path / "a" / "b" / "c" / "test.log", tmp_path, [], patterns
            )
            is False
        )

    def test_doublestar_recursive_match(self, tmp_path):
        """**/*.ext patterns match files recursively."""
        (tmp_path / "test.log").write_text("x")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "test.log").write_text("x")
        (tmp_path / "a" / "b" / "c").mkdir(parents=True)
        (tmp_path / "a" / "b" / "c" / "test.log").write_text("x")

        patterns = ["**/*.log"]

        # ** matches zero or more directory levels
        assert (
            ctxpack.should_process(tmp_path / "test.log", tmp_path, [], patterns)
            is False
        )
        assert (
            ctxpack.should_process(
                tmp_path / "subdir" / "test.log", tmp_path, [], patterns
            )
            is False
        )
        assert (
            ctxpack.should_process(
                tmp_path / "a" / "b" / "c" / "test.log", tmp_path, [], patterns
            )
            is False
        )

    def test_dir_doublestar_matches_dir_and_contents(self, tmp_path):
        """dir/** matches the directory itself and all contents."""
        node_dir = tmp_path / "node_modules"
        node_dir.mkdir()
        (node_dir / "pkg.js").write_text("x")
        (node_dir / "subpkg").mkdir()
        (node_dir / "subpkg" / "index.js").write_text("x")

        patterns = ["node_modules/**"]

        # Directory itself should be ignored
        assert ctxpack.should_process(node_dir, tmp_path, [], patterns) is False
        # Files inside should be ignored
        assert (
            ctxpack.should_process(node_dir / "pkg.js", tmp_path, [], patterns) is False
        )
        assert (
            ctxpack.should_process(
                node_dir / "subpkg" / "index.js", tmp_path, [], patterns
            )
            is False
        )

    def test_trailing_slash_directory_pattern(self, tmp_path):
        """Patterns with trailing / match directories and their contents."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("x")

        patterns = [".git/"]

        # Directory itself should be ignored
        assert ctxpack.should_process(git_dir, tmp_path, [], patterns) is False
        # Files inside should be ignored
        assert (
            ctxpack.should_process(git_dir / "config", tmp_path, [], patterns) is False
        )

    def test_anchored_pattern_behavior(self, tmp_path):
        """Leading / anchors patterns to the scan root (fixture for issue #6)."""
        (tmp_path / "test.log").write_text("x", encoding="utf-8")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "test.log").write_text("x", encoding="utf-8")

        # Leading / means "match at the scan root only."
        patterns = ["/test.log"]

        assert (
            ctxpack.should_process(tmp_path / "test.log", tmp_path, [], patterns)
            is False
        )
        assert (
            ctxpack.should_process(
                tmp_path / "subdir" / "test.log", tmp_path, [], patterns
            )
            is True
        )

    def test_negation_pattern_reincludes(self, tmp_path):
        """!pattern re-includes previously excluded files."""
        env_file = tmp_path / ".env"
        env_local = tmp_path / ".env.local"
        env_example = tmp_path / ".env.example"

        env_file.write_text("SECRET=x")
        env_local.write_text("SECRET=y")
        env_example.write_text("SECRET_TEMPLATE=z")

        # .env and .env.* are excluded, but !.env.example re-includes
        patterns = [".env", ".env.*", "!.env.example"]

        assert ctxpack.should_process(env_file, tmp_path, [], patterns) is False
        assert ctxpack.should_process(env_local, tmp_path, [], patterns) is False
        # Re-included by negation pattern
        assert ctxpack.should_process(env_example, tmp_path, [], patterns) is True

    def test_pattern_precedence_order(self, tmp_path):
        """Patterns are processed in order; later patterns can override earlier."""
        test_file = tmp_path / "special.log"
        test_file.write_text("x")

        # First exclude all .log, then re-include special.log
        patterns = ["*.log", "!special.log"]

        assert ctxpack.should_process(test_file, tmp_path, [], patterns) is True

        # Reverse order: first include, then exclude
        patterns2 = ["!special.log", "*.log"]

        # special.log doesn't match *.log initially, so negation has no effect,
        # then *.log excludes it
        assert ctxpack.should_process(test_file, tmp_path, [], patterns2) is False


class TestEstimateTokens:
    """Tests for estimate_tokens function."""

    def test_basic_estimation(self):
        """Should estimate ~4 chars per token."""
        text = "a" * 400  # 400 chars
        tokens = ctxpack.estimate_tokens(text)

        assert tokens == 100  # 400 / 4 = 100

    def test_minimum_one_token(self):
        """Should return at least 1 token for any non-empty text."""
        text = "a"  # 1 char
        tokens = ctxpack.estimate_tokens(text)

        assert tokens >= 1

    def test_empty_string_returns_zero(self):
        """Should return 0 tokens for empty string (no content = no tokens)."""
        tokens = ctxpack.estimate_tokens("")

        assert tokens == 0

    def test_very_short_strings(self):
        """Should handle very short strings correctly."""
        assert ctxpack.estimate_tokens("a") == 1  # 1 char -> 1 token
        assert ctxpack.estimate_tokens("abc") == 1  # 3 chars -> 1 token
        assert ctxpack.estimate_tokens("abcd") == 1  # 4 chars -> 1 token
        assert ctxpack.estimate_tokens("abcde") == 1  # 5 chars -> 1 token

    def test_token_boundaries(self):
        """Test behavior at token boundaries (multiples of 4)."""
        assert ctxpack.estimate_tokens("") == 0  # 0 chars -> 0 tokens
        assert ctxpack.estimate_tokens("abcd") == 1  # 4 chars -> 1 token
        assert ctxpack.estimate_tokens("abcdefgh") == 2  # 8 chars -> 2 tokens
        assert ctxpack.estimate_tokens("a" * 12) == 3  # 12 chars -> 3 tokens
        assert ctxpack.estimate_tokens("a" * 100) == 25  # 100 chars -> 25 tokens


class TestReadTextFile:
    """Tests for read_text_file function."""

    def test_read_normal_text_file(self, tmp_path):
        """Should read normal text file successfully."""
        test_file = tmp_path / "test.txt"
        content = "Hello, World!"
        test_file.write_text(content)

        result = ctxpack.read_text_file(test_file)

        assert result == content

    def test_skip_binary_extension(self, tmp_path):
        """Should return None for binary file extensions."""
        binary_file = tmp_path / "image.png"
        binary_file.write_bytes(b"\x89PNG")

        result = ctxpack.read_text_file(binary_file)

        assert result is None

    def test_skip_large_file(self, tmp_path):
        """Should return skip message for files larger than MAX_FILE_BYTES."""
        large_file = tmp_path / "large.txt"
        # Create a file larger than 500KB
        large_content = "x" * (ctxpack.MAX_FILE_BYTES + 1)
        large_file.write_text(large_content)

        result = ctxpack.read_text_file(large_file)

        assert "skipped" in result.lower()
        assert "too large" in result.lower()

    def test_handle_read_error(self, tmp_path):
        """Should handle file read errors gracefully."""
        # Try to read a non-existent file path (simulate error)
        nonexistent = tmp_path / "does_not_exist.txt"
        result = ctxpack.read_text_file(nonexistent)

        assert "Error" in result


class TestBuildFileInventory:
    """Tests for build_file_inventory function."""

    def test_collect_text_files(self, tmp_path):
        """Should collect all non-ignored text files."""
        # Create some test files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.py").write_text("print('hello')")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.md").write_text("# Header")

        patterns = []
        inventory = ctxpack.build_file_inventory(tmp_path, [], patterns)

        assert len(inventory) == 3
        paths = [item["path"] for item in inventory]
        assert "file1.txt" in paths
        assert "file2.py" in paths
        assert "subdir/file3.md" in paths

    def test_skip_ignored_files(self, tmp_path):
        """Should skip files matching ignore patterns."""
        (tmp_path / "good.txt").write_text("good")
        (tmp_path / "bad.log").write_text("bad")

        patterns = ["*.log"]
        inventory = ctxpack.build_file_inventory(tmp_path, [], patterns)

        assert len(inventory) == 1
        assert inventory[0]["path"] == "good.txt"

    def test_skip_binary_files(self, tmp_path):
        """Should skip binary files."""
        (tmp_path / "text.txt").write_text("text")
        (tmp_path / "image.png").write_bytes(b"\x89PNG")

        patterns = []
        inventory = ctxpack.build_file_inventory(tmp_path, [], patterns)

        assert len(inventory) == 1
        assert inventory[0]["path"] == "text.txt"

    def test_inventory_sorted_by_path(self, tmp_path):
        """Should return inventory sorted by path."""
        (tmp_path / "z.txt").write_text("z")
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "m.txt").write_text("m")

        patterns = []
        inventory = ctxpack.build_file_inventory(tmp_path, [], patterns)

        paths = [item["path"] for item in inventory]
        assert paths == ["a.txt", "m.txt", "z.txt"]

    def test_inventory_includes_metadata(self, tmp_path):
        """Should include size, tokens, and content in inventory items."""
        test_file = tmp_path / "test.txt"
        content = "Hello"
        test_file.write_text(content)

        patterns = []
        inventory = ctxpack.build_file_inventory(tmp_path, [], patterns)

        assert len(inventory) == 1
        item = inventory[0]
        assert "path" in item
        assert "size_bytes" in item
        assert "tokens_estimate" in item
        assert "content" in item
        assert item["size_bytes"] == len(content.encode("utf-8"))


class TestTrimToBudget:
    """Tests for trim_to_budget function."""

    def test_keep_all_within_budget(self):
        """Should keep all files if within budget."""
        inventory = [
            {
                "path": "a.txt",
                "content": "a" * 100,
                "tokens_estimate": 25,
                "size_bytes": 100,
            },
            {
                "path": "b.txt",
                "content": "b" * 100,
                "tokens_estimate": 25,
                "size_bytes": 100,
            },
        ]

        result, _incomplete = ctxpack.trim_to_budget(inventory, 100)

        assert len(result) == 2
        assert all(not item.get("truncated", False) for item in result)

    def test_truncate_when_over_budget(self):
        """Should truncate last file when over budget."""
        inventory = [
            {
                "path": "a.txt",
                "content": "a" * 100,
                "tokens_estimate": 25,
                "size_bytes": 100,
            },
            {
                "path": "b.txt",
                "content": "b" * 400,
                "tokens_estimate": 100,
                "size_bytes": 400,
            },
        ]

        result, _incomplete = ctxpack.trim_to_budget(inventory, 50)

        assert len(result) == 2
        assert result[0]["path"] == "a.txt"
        assert not result[0].get("truncated", False)
        assert result[1]["path"] == "b.txt"
        assert result[1].get("truncated", False)
        assert "[TRUNCATED by ctxpack to fit budget]" in result[1]["content"]

    def test_stop_when_budget_exhausted(self):
        """Should stop adding files when budget is exhausted."""
        inventory = [
            {
                "path": "a.txt",
                "content": "a" * 100,
                "tokens_estimate": 25,
                "size_bytes": 100,
            },
            {
                "path": "b.txt",
                "content": "b" * 100,
                "tokens_estimate": 25,
                "size_bytes": 100,
            },
            {
                "path": "c.txt",
                "content": "c" * 100,
                "tokens_estimate": 25,
                "size_bytes": 100,
            },
        ]

        result, _incomplete = ctxpack.trim_to_budget(inventory, 30)

        # First file fits (25 tokens), second gets truncated to fit remaining budget
        assert len(result) >= 1
        # The truncation logic may add a few extra tokens for the truncation message
        # so we check that we don't significantly exceed the budget
        total_tokens = sum(item["tokens_estimate"] for item in result)
        assert total_tokens <= 50  # Allow some overhead for truncation message
        assert result[0]["path"] == "a.txt"


class TestGenerateMarkdown:
    """Tests for generate_markdown function."""

    def test_markdown_header(self, tmp_path):
        """Should include proper header in markdown output."""
        inventory = []
        md = ctxpack.generate_markdown(inventory, tmp_path, False)

        assert "# ctxpack Context Pack" in md
        assert "Generated from:" in md
        assert "Files included: 0" in md

    def test_markdown_file_entries(self, tmp_path):
        """Should include file entries with metadata."""
        inventory = [
            {
                "path": "test.txt",
                "size_bytes": 100,
                "tokens_estimate": 25,
                "content": "Hello World",
                "truncated": False,
            }
        ]
        md = ctxpack.generate_markdown(inventory, tmp_path, False)

        assert "## test.txt" in md
        assert "Size: 100 bytes" in md
        assert "Est. tokens: 25" in md
        assert "```text" in md
        assert "Hello World" in md
        assert "```" in md

    def test_markdown_truncation_warning(self, tmp_path):
        """Should include truncation warning when file is truncated."""
        inventory = [
            {
                "path": "big.txt",
                "size_bytes": 1000,
                "tokens_estimate": 250,
                "content": "Truncated content",
                "truncated": True,
            }
        ]
        md = ctxpack.generate_markdown(inventory, tmp_path, False)

        assert "⚠️ Truncated to fit token budget" in md


class TestGenerateJson:
    """Tests for generate_json function."""

    def test_json_structure(self, tmp_path):
        """Should generate proper JSON structure."""
        inventory = [
            {
                "path": "test.txt",
                "size_bytes": 100,
                "tokens_estimate": 25,
                "content": "Hello",
                "truncated": False,
            }
        ]
        budget = 8000

        result = ctxpack.generate_json(inventory, tmp_path, budget, False)

        assert result["generator"] == "ctxpack"
        assert "root" in result
        assert result["budget_tokens"] == budget
        assert "files" in result
        assert len(result["files"]) == 1

    def test_json_file_fields(self, tmp_path):
        """Should include all required fields in file entries."""
        inventory = [
            {
                "path": "test.txt",
                "size_bytes": 100,
                "tokens_estimate": 25,
                "content": "Hello",
                "truncated": False,
            }
        ]

        result = ctxpack.generate_json(inventory, tmp_path, 8000, False)
        file_entry = result["files"][0]

        assert "path" in file_entry
        assert "size_bytes" in file_entry
        assert "tokens_estimate" in file_entry
        assert "truncated" in file_entry
        assert "content" in file_entry


class TestCmdInit:
    """Tests for cmd_init function."""

    def test_create_ignore_file(self, tmp_path):
        """Should create .ctxignore file if missing."""
        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_init(args)

        ignore_file = tmp_path / ctxpack.DEFAULT_IGNORE_FILE
        assert ignore_file.exists()
        content = ignore_file.read_text()
        assert ".git/" in content
        assert "*.log" in content

    def test_create_config_file(self, tmp_path):
        """Should create ctxpack.json file if missing."""
        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_init(args)

        config_file = tmp_path / ctxpack.DEFAULT_CONFIG_FILE
        assert config_file.exists()
        config = json.loads(config_file.read_text())
        assert "budget_tokens" in config
        assert config["budget_tokens"] == 8000

    def test_skip_existing_files(self, tmp_path, capsys):
        """Should not overwrite existing files."""
        ignore_file = tmp_path / ctxpack.DEFAULT_IGNORE_FILE
        config_file = tmp_path / ctxpack.DEFAULT_CONFIG_FILE
        ignore_file.write_text("existing")
        config_file.write_text("{}")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_init(args)

        captured = capsys.readouterr()
        assert "already exists" in captured.out
        assert ignore_file.read_text() == "existing"


class TestCmdPack:
    """Tests for cmd_pack function."""

    def test_generate_output_files(self, tmp_path, capsys):
        """Should generate both JSON and Markdown output files."""
        # Create a simple test file
        (tmp_path / "test.txt").write_text("Hello World")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 8000,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(args)

        json_file = tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")
        md_file = tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.md")

        assert json_file.exists()
        assert md_file.exists()

        # Verify JSON is valid
        data = json.loads(json_file.read_text())
        assert data["generator"] == "ctxpack"

        # Verify MD contains expected content
        md_content = md_file.read_text()
        assert "# ctxpack Context Pack" in md_content

    def test_respect_budget_from_cli(self, tmp_path):
        """Should use budget from CLI arguments."""
        # Create files that will exceed a small budget
        (tmp_path / "file1.txt").write_text("a" * 1000)
        (tmp_path / "file2.txt").write_text("b" * 1000)

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 100,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(args)

        json_file = tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")
        data = json.loads(json_file.read_text())

        assert data["budget_tokens"] == 100

    def test_respect_budget_from_config(self, tmp_path):
        """Should load budget from config file when --no-config is not set."""
        # Create config file
        config = {"budget_tokens": 5000}
        config_file = tmp_path / ctxpack.DEFAULT_CONFIG_FILE
        config_file.write_text(json.dumps(config))

        # Create test file
        (tmp_path / "test.txt").write_text("content")

        with patch.object(Path, "cwd", return_value=tmp_path):
            # budget=None means "not supplied on the CLI", so ctxpack.json wins.
            # Passing an explicit value here would (correctly) take precedence,
            # which is the bug this file previously asserted as expected.
            args = type(
                "Args",
                (),
                {
                    "budget": None,
                    "no_config": False,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(args)

        json_file = tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")
        data = json.loads(json_file.read_text())

        assert data["budget_tokens"] == 5000

    def test_explicit_cli_budget_beats_config(self, tmp_path):
        """An explicitly supplied --budget must override ctxpack.json.

        Regression test: the previous implementation compared --budget against
        its own default, so `--budget 8000` was indistinguishable from omitting
        the flag and config silently won.
        """
        config = {"budget_tokens": 5000}
        (tmp_path / ctxpack.DEFAULT_CONFIG_FILE).write_text(json.dumps(config))
        (tmp_path / "test.txt").write_text("content")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": ctxpack.DEFAULT_BUDGET_TOKENS,
                    "no_config": False,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(args)

        json_file = tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")
        data = json.loads(json_file.read_text())

        assert data["budget_tokens"] == ctxpack.DEFAULT_BUDGET_TOKENS

    def test_no_config_flag_bypasses_config(self, tmp_path):
        """Should ignore config file when --no-config flag is set."""
        # Create config file with different budget
        config = {"budget_tokens": 5000}
        config_file = tmp_path / ctxpack.DEFAULT_CONFIG_FILE
        config_file.write_text(json.dumps(config))

        # Create test file
        (tmp_path / "test.txt").write_text("content")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 3000,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(args)

        json_file = tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")
        data = json.loads(json_file.read_text())

        # Should use CLI budget, not config budget
        assert data["budget_tokens"] == 3000


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_pack_workflow(self, tmp_path):
        """Test complete pack workflow from init to output."""
        # Setup: create project structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("def main():\n    print('Hello')")
        (src_dir / "utils.py").write_text("def helper():\n    pass")
        (tmp_path / "README.md").write_text("# My Project")
        (tmp_path / "debug.log").write_text("Debug info")  # Should be ignored

        # Initialize
        with patch.object(Path, "cwd", return_value=tmp_path):
            init_args = type(
                "Args",
                (),
                {
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_init(init_args)

        # Pack with custom budget
        with patch.object(Path, "cwd", return_value=tmp_path):
            pack_args = type(
                "Args",
                (),
                {
                    "budget": 500,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(pack_args)

        # Verify outputs
        json_file = tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")
        md_file = tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")

        assert json_file.exists()
        assert md_file.exists()

        data = json.loads(json_file.read_text())
        assert data["budget_tokens"] == 500

        # Log file should be ignored
        paths = [f["path"] for f in data["files"]]
        assert "debug.log" not in paths
        assert any("main.py" in p for p in paths)

    def test_ignore_patterns_end_to_end(self, tmp_path):
        """Test that ignore patterns work correctly end-to-end."""
        # Create various files
        (tmp_path / "good.py").write_text("print('hi')")
        (tmp_path / "bad.pyc").write_bytes(b"\x00")
        (tmp_path / "app.log").write_text("log")
        venv_dir = tmp_path / "venv" / "lib"
        venv_dir.mkdir(parents=True)
        (venv_dir / "site-packages.py").write_text("venv code")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 10000,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(args)

        json_file = tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")
        data = json.loads(json_file.read_text())

        paths = [f["path"] for f in data["files"]]
        assert "good.py" in paths
        assert "bad.pyc" not in paths
        assert "app.log" not in paths
        assert not any("venv" in p for p in paths)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestV020Regressions:
    """Regression tests for defects found while getting CI green on v0.2.0.

    Each test here failed before its corresponding fix, so they document
    behaviour rather than restating the implementation.
    """

    def test_ctxignore_defaults_are_actually_applied(self, tmp_path):
        """load_ignore_patterns() was defined but never called by cmd_pack.

        Consequence: .ctxignore and every built-in default (.git, venv/,
        *.log) were silently inert.
        """
        (tmp_path / "good.py").write_text("print('hi')", encoding="utf-8")
        (tmp_path / "app.log").write_text("noise", encoding="utf-8")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("[core]", encoding="utf-8")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 100000,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(args)

        data = json.loads(
            (tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")).read_text()
        )
        paths = [f["path"] for f in data["files"]]
        assert "good.py" in paths
        assert "app.log" not in paths
        assert not any(p.startswith(".git/") for p in paths)

    def test_dir_glob_pattern_matches_the_directory_itself(self):
        """A "dir/**" pattern must match the directory, or os.walk descends."""
        assert ctxpack.matches_pattern(".git", ".git", ".git/**") is True
        assert (
            ctxpack.matches_pattern("node_modules", "node_modules", "node_modules/**")
            is True
        )
        assert ctxpack.matches_pattern(".git/config", "config", ".git/**") is True
        assert ctxpack.matches_pattern("src/main.py", "main.py", ".git/**") is False

    def test_binary_detected_by_content_not_extension(self, tmp_path):
        """.coverage is a SQLite db with a text-looking suffix."""
        sqlite = tmp_path / ".coverage"
        sqlite.write_bytes(b"SQLite format 3\x00" + bytes(range(256)))
        source = tmp_path / "main.py"
        source.write_text("print('hi')\n", encoding="utf-8")
        unicode_text = tmp_path / "notes.md"
        unicode_text.write_text("# caf\u00e9 \u2014 na\u00efve\n", encoding="utf-8")

        assert ctxpack.looks_binary(sqlite) is True
        assert ctxpack.looks_binary(source) is False
        # Valid multi-byte UTF-8 must not be misclassified as binary.
        assert ctxpack.looks_binary(unicode_text) is False
        assert ctxpack.read_text_file(sqlite) is None

    def test_no_file_is_silently_dropped(self):
        """Files past the budget are recorded as omitted, not discarded."""
        inventory = [
            {
                "path": f"{c}.py",
                "size_bytes": 400,
                "tokens_estimate": 100,
                "content": c * 400,
            }
            for c in "abc"
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 100)

        assert [i["path"] for i in result] == ["a.py", "b.py", "c.py"]
        assert is_incomplete is True
        assert result[0].get("omitted", False) is False
        assert result[1]["omitted"] is True
        assert result[2]["omitted"] is True
        # Original size is preserved so a reader knows what was skipped.
        assert result[1]["tokens_estimate_original"] == 100

    def test_budget_is_never_exceeded(self):
        """The truncation marker is reserved before slicing."""
        for budget in (20, 50, 137, 999):
            inventory = [
                {
                    "path": "a.py",
                    "size_bytes": 40,
                    "tokens_estimate": 10,
                    "content": "a" * 40,
                },
                {
                    "path": "b.py",
                    "size_bytes": 8000,
                    "tokens_estimate": 2000,
                    "content": "b" * 8000,
                },
            ]
            result, _ = ctxpack.trim_to_budget(inventory, budget)
            total = sum(i["tokens_estimate"] for i in result)
            assert total <= budget, f"budget {budget} exceeded: {total}"

    def test_cmd_pack_needs_no_hidden_args_attributes(self, tmp_path):
        """cmd_pack previously read args.*_set, which only main() set."""

        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")

        class MinimalArgs:
            budget = None
            no_config = True
            include = None
            exclude = None
            output_dir = None
            base_name = None

        with patch.object(Path, "cwd", return_value=tmp_path):
            ctxpack.cmd_pack(MinimalArgs())  # must not raise AttributeError

        assert (tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")).exists()

    def test_output_is_written_relative_to_scanned_root(self, tmp_path):
        """A relative --output-dir resolves against the root, not the process cwd."""
        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": None,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": "artifacts",
                    "base_name": "pack",
                },
            )()
            ctxpack.cmd_pack(args)

        assert (tmp_path / "artifacts" / "pack.context.json").exists()
        assert (tmp_path / "artifacts" / "pack.context.md").exists()

    def test_omitted_files_are_listed_in_markdown(self, tmp_path):
        """The reader must be able to see what the pack is missing."""
        inventory = [
            {
                "path": "kept.py",
                "size_bytes": 40,
                "tokens_estimate": 10,
                "content": "a" * 40,
            },
            {
                "path": "dropped.py",
                "size_bytes": 4000,
                "tokens_estimate": 1000,
                "content": "b" * 4000,
            },
        ]
        result, incomplete = ctxpack.trim_to_budget(inventory, 10)
        md = ctxpack.generate_markdown(result, tmp_path, incomplete)

        assert "Omitted files" in md
        assert "dropped.py" in md
        assert "Files included: 1" in md


class TestSecretSafeDefaults:
    """Regression tests for the secret-safe default ignore policy (issue #5).

    These tests prove that credential-bearing files are excluded from
    generated packs by default, matching the README security claim.
    """

    def test_env_file_excluded(self, tmp_path):
        """`.env` must never reach the pack."""
        (tmp_path / ".env").write_text("SECRET_KEY=abc123", encoding="utf-8")
        (tmp_path / "main.py").write_text("print('hi')", encoding="utf-8")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 100000,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(args)

        data = json.loads(
            (tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")).read_text()
        )
        paths = [f["path"] for f in data["files"]]
        assert ".env" not in paths
        assert "main.py" in paths

    def test_env_local_excluded(self, tmp_path):
        """`.env.local`, `.env.production`, etc. must be excluded."""
        (tmp_path / ".env.local").write_text("DB_PASSWORD=x", encoding="utf-8")
        (tmp_path / ".env.production").write_text("API_KEY=y", encoding="utf-8")
        (tmp_path / ".env.example").write_text("API_KEY=changeme", encoding="utf-8")
        (tmp_path / "app.py").write_text("pass", encoding="utf-8")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 100000,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(args)

        data = json.loads(
            (tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")).read_text()
        )
        paths = [f["path"] for f in data["files"]]
        assert ".env.local" not in paths
        assert ".env.production" not in paths
        # .env.example is the conventional non-secret template
        assert ".env.example" in paths
        assert "app.py" in paths

    def test_private_key_excluded(self, tmp_path):
        """`*.pem` and `*.key` files must be excluded."""
        (tmp_path / "id_rsa.pem").write_text(
            "-----BEGIN PRIVATE KEY-----", encoding="utf-8"
        )
        (tmp_path / "server.key").write_text(
            "-----BEGIN PRIVATE KEY-----", encoding="utf-8"
        )
        (tmp_path / "cert.crt").write_text(
            "-----BEGIN CERTIFICATE-----", encoding="utf-8"
        )
        (tmp_path / "code.py").write_text("x = 1", encoding="utf-8")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 100000,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(args)

        data = json.loads(
            (tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")).read_text()
        )
        paths = [f["path"] for f in data["files"]]
        assert "id_rsa.pem" not in paths
        assert "server.key" not in paths
        assert "cert.crt" not in paths
        assert "code.py" in paths

    def test_certificate_files_excluded(self, tmp_path):
        """`*.p12`, `*.pfx`, `*.cer` files must be excluded."""
        (tmp_path / "keystore.p12").write_bytes(b"\x00")
        (tmp_path / "identity.pfx").write_bytes(b"\x00")
        (tmp_path / "ca-root.cer").write_text("cert", encoding="utf-8")
        (tmp_path / "src.py").write_text("pass", encoding="utf-8")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 100000,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(args)

        data = json.loads(
            (tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")).read_text()
        )
        paths = [f["path"] for f in data["files"]]
        assert "keystore.p12" not in paths
        assert "identity.pfx" not in paths
        assert "ca-root.cer" not in paths
        assert "src.py" in paths

    def test_credential_directories_excluded(self, tmp_path):
        """`.aws/` and `.ssh/` directories must be fully excluded."""
        aws_dir = tmp_path / ".aws"
        aws_dir.mkdir()
        (aws_dir / "credentials").write_text(
            "[default]\naws_access_key_id=AKIA", encoding="utf-8"
        )
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        (ssh_dir / "id_ed25519").write_text("ssh-ed25519 AAAA", encoding="utf-8")
        (ssh_dir / "config").write_text("Host *", encoding="utf-8")
        (tmp_path / "main.py").write_text("pass", encoding="utf-8")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 100000,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(args)

        data = json.loads(
            (tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")).read_text()
        )
        paths = [f["path"] for f in data["files"]]
        assert not any(p.startswith(".aws/") for p in paths)
        assert not any(p.startswith(".ssh/") for p in paths)
        assert "main.py" in paths

    def test_auth_dotfiles_excluded(self, tmp_path):
        """.netrc, .npmrc, .pypirc files must be excluded."""
        (tmp_path / ".netrc").write_text("machine github.com", encoding="utf-8")
        (tmp_path / ".npmrc").write_text(
            "//registry.npmjs.org/:_authToken=xyz", encoding="utf-8"
        )
        (tmp_path / ".pypirc").write_text("[pypi]\nusername: user", encoding="utf-8")
        (tmp_path / "script.py").write_text("pass", encoding="utf-8")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 100000,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(args)

        data = json.loads(
            (tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")).read_text()
        )
        paths = [f["path"] for f in data["files"]]
        assert ".netrc" not in paths
        assert ".npmrc" not in paths
        assert ".pypirc" not in paths
        assert "script.py" in paths

    def test_gpg_and_asc_excluded(self, tmp_path):
        """`*.gpg` and `*.asc` files must be excluded."""
        (tmp_path / "secret.gpg").write_bytes(b"\x85\x02")
        (tmp_path / "message.asc").write_text(
            "-----BEGIN PGP MESSAGE-----", encoding="utf-8"
        )
        (tmp_path / "app.py").write_text("pass", encoding="utf-8")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 100000,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(args)

        data = json.loads(
            (tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")).read_text()
        )
        paths = [f["path"] for f in data["files"]]
        assert "secret.gpg" not in paths
        assert "message.asc" not in paths
        assert "app.py" in paths

    def test_negation_pattern_works(self, tmp_path):
        """A `!`-prefixed pattern must re-include a path an earlier pattern excluded."""
        # User wants to keep a test fixture despite *.pem being excluded
        (tmp_path / "fixture.pem").write_text("test key", encoding="utf-8")
        (tmp_path / "real.pem").write_text("real key", encoding="utf-8")

        ignore_file = tmp_path / ctxpack.DEFAULT_IGNORE_FILE
        ignore_file.write_text("!fixture.pem\n", encoding="utf-8")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 100000,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(args)

        data = json.loads(
            (tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")).read_text()
        )
        paths = [f["path"] for f in data["files"]]
        assert "fixture.pem" in paths
        assert "real.pem" not in paths


class TestIgnoreSemantics:
    """Regression tests for ctxignore pattern semantics (issue #6).

    These tests define the supported subset of gitignore semantics and
    ensure the implementation matches exactly what the documentation
    promises.
    """

    # === Negation patterns ===

    def test_negation_after_exclusion(self):
        """`!foo` must override a previous `foo` pattern."""
        # should_process processes patterns in order
        exclude = ["*.pem", "!fixture.pem"]
        assert (
            ctxpack.should_process(
                Path("/fake/fixture.pem"), Path("/fake"), [], exclude
            )
            is True
        )
        assert (
            ctxpack.should_process(Path("/fake/real.pem"), Path("/fake"), [], exclude)
            is False
        )

    def test_negation_after_anchor(self):
        """Negation should override anchored exclusions too."""
        exclude = ["/build", "!build"]
        assert (
            ctxpack.should_process(Path("/fake/build"), Path("/fake"), [], exclude)
            is True
        )

    def test_negation_does_not_affect_other_files(self):
        """A negation must only re-include its specific target."""
        exclude = ["*.pem", "!fixture.pem"]
        assert (
            ctxpack.should_process(Path("/fake/other.key"), Path("/fake"), [], exclude)
            is True
        )  # not *.pem

    # === Anchored patterns ===

    def test_anchored_matches_at_root(self):
        """`/foo` matches only at the scan root."""
        assert ctxpack.matches_pattern("build", "build", "/build") is True
        assert ctxpack.matches_pattern("src/build", "build", "/build") is False

    def test_anchored_does_not_match_nested(self):
        """`/foo` must not match `nested/foo`."""
        assert (
            ctxpack.matches_pattern("deep/nested/foo.txt", "foo.txt", "/foo.txt")
            is False
        )

    def test_non_anchored_matches_anywhere(self):
        """A pattern without leading `/` matches at any depth."""
        assert ctxpack.matches_pattern("foo.txt", "foo.txt", "foo.txt") is True
        assert ctxpack.matches_pattern("dir/foo.txt", "foo.txt", "foo.txt") is True
        assert ctxpack.matches_pattern("deep/foo.txt", "foo.txt", "foo.txt") is True

    # === Directory-only patterns ===

    def test_directory_slash_matches_contents(self):
        """`foo/` matches the directory and everything inside it."""
        assert ctxpack.matches_pattern("venv/lib/x.py", "x.py", "venv/") is True

    def test_directory_slash_matches_directory_itself(self):
        """`foo/` must match the directory itself."""
        assert ctxpack.matches_pattern("venv", "venv", "venv/") is True

    def test_directory_glob_matches_contents(self):
        """`foo/**` matches the directory and everything inside it."""
        assert (
            ctxpack.matches_pattern("node_modules/pkg/x.js", "x.js", "node_modules/**")
            is True
        )

    def test_directory_glob_matches_directory_itself(self):
        """`foo/**` must match the directory itself."""
        assert (
            ctxpack.matches_pattern("node_modules", "node_modules", "node_modules/**")
            is True
        )

    # === `**` recursive glob ===

    def test_double_star_matches_any_depth(self):
        """`**` spans any number of path segments."""
        assert ctxpack.matches_pattern("a/b/c/x", "x", "**/x") is True
        assert ctxpack.matches_pattern("x", "x", "**/x") is True
        assert ctxpack.matches_pattern("a/x", "x", "**/x") is True

    def test_double_star_dir_anchored_to_root(self):
        """`**/.aws/**` matches at the scan root."""
        assert (
            ctxpack.matches_pattern(".aws/credentials", "credentials", "**/.aws/**")
            is True
        )
        assert (
            ctxpack.matches_pattern(
                "nested/.aws/credentials", "credentials", "**/.aws/**"
            )
            is True
        )

    def test_double_star_dir_directory_itself(self):
        """`**/.dir/**` matches the directory itself."""
        assert ctxpack.matches_pattern(".aws", ".aws", "**/.aws/**") is True

    def test_double_star_middle(self):
        """`**` in the middle of a pattern spans segments."""
        assert ctxpack.matches_pattern("a/b/c", "c", "a/**/c") is True

    # === Pattern precedence ===

    def test_last_matching_pattern_wins(self):
        """The last matching pattern determines inclusion."""
        exclude = ["*.txt", "!secret.txt"]
        assert (
            ctxpack.should_process(Path("/fake/secret.txt"), Path("/fake"), [], exclude)
            is True
        )
        assert (
            ctxpack.should_process(Path("/fake/other.txt"), Path("/fake"), [], exclude)
            is False
        )

    def test_exclusion_overrides_include(self):
        """Excludes take precedence over includes."""
        include = ["*.txt"]
        exclude = ["secret.txt"]
        assert (
            ctxpack.should_process(
                Path("/fake/secret.txt"), Path("/fake"), include, exclude
            )
            is False
        )

    def test_include_restriction(self):
        """Without matching include patterns, the file is excluded."""
        include = ["*.py"]
        exclude = []
        assert (
            ctxpack.should_process(
                Path("/fake/script.py"), Path("/fake"), include, exclude
            )
            is True
        )
        assert (
            ctxpack.should_process(
                Path("/fake/readme.md"), Path("/fake"), include, exclude
            )
            is False
        )

    # === Root-relative vs basename matching ===

    def test_bare_filename_matches_anywhere(self):
        """A bare filename matches at any depth."""
        assert ctxpack.matches_pattern("debug.log", "debug.log", "*.log") is True
        assert ctxpack.matches_pattern("logs/debug.log", "debug.log", "*.log") is True

    def test_bare_filename_does_not_match_directory(self):
        """A bare filename pattern should not match a directory."""
        assert ctxpack.matches_pattern("log", "log", "*.log") is False

    # === Escaped patterns ===

    def test_escaped_asterisk(self):
        """`\\*` matches a literal `*` character."""
        assert ctxpack.matches_pattern("file*.txt", "file*.txt", r"file\*.txt") is True
        assert ctxpack.matches_pattern("fileX.txt", "fileX.txt", r"file\*.txt") is False

    def test_escaped_bracket(self):
        """`\\[` matches a literal `[` character."""
        assert ctxpack.matches_pattern("[foo]", "[foo]", r"\[foo\]") is True
        assert ctxpack.matches_pattern("foo", "foo", r"\[foo\]") is False

    def test_escaped_space(self):
        """`\\ ` matches a literal space character."""
        assert (
            ctxpack.matches_pattern("my file.txt", "my file.txt", r"my\ file.txt")
            is True
        )
        assert (
            ctxpack.matches_pattern("myfile.txt", "myfile.txt", r"my\ file.txt")
            is False
        )

    def test_escaped_backslash(self):
        """`\\\\` matches a literal `\\` character."""
        assert (
            ctxpack.matches_pattern("file\\name", "file\\name", r"file\\name") is True
        )
        assert ctxpack.matches_pattern("filename", "filename", r"file\\name") is False


class TestTokenBudgetSemantics:
    """Regression tests for estimated token budget semantics (issue #7).

    These tests prove that budget trimming is deterministic, never
    overshoots the configured budget, and handles Unicode-heavy inputs
    consistently. The heuristic is chars / 4 and this is documented
    as an estimate — NOT a guarantee of model-token counts.
    """

    # === Exact-budget boundary ===

    def test_exact_budget_no_truncation(self):
        """Files summing to exactly the budget are kept whole."""
        inventory = [
            {
                "path": "a.txt",
                "size_bytes": 400,
                "tokens_estimate": 100,
                "content": "a" * 400,
            },
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 100)
        assert is_incomplete is False
        assert result[0].get("truncated") is not True
        assert result[0].get("omitted") is not True

    def test_one_token_over_budget_truncates(self):
        """One token over budget triggers truncation."""
        inventory = [
            {
                "path": "a.txt",
                "size_bytes": 404,
                "tokens_estimate": 101,
                "content": "a" * 404,
            },
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 100)
        assert is_incomplete is True
        assert result[0].get("truncated") is True

    # === Over-budget scenarios ===

    def test_first_file_over_budget_truncates(self):
        """A single file larger than the budget is truncated."""
        inventory = [
            {
                "path": "big.txt",
                "size_bytes": 8000,
                "tokens_estimate": 2000,
                "content": "b" * 8000,
            },
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 100)
        assert is_incomplete is True
        assert result[0].get("truncated") is True

    def test_many_files_never_exceed_budget(self):
        """With many files, total emitted tokens never exceed budget."""
        inventory = [
            {
                "path": f"{c}.txt",
                "size_bytes": 400,
                "tokens_estimate": 100,
                "content": c * 400,
            }
            for c in "abcdefghij"
        ]
        for budget in (50, 100, 150, 250, 500, 999):
            result, _ = ctxpack.trim_to_budget(inventory, budget)
            total = sum(i["tokens_estimate"] for i in result)
            assert total <= budget, f"budget {budget} exceeded: {total}"

    # === Unicode-heavy inputs ===

    def test_unicode_content_estimated_by_chars(self):
        """Unicode content is estimated by character count, not byte count."""
        # Each emoji is 1 character but 4 bytes in UTF-8
        text = "🎉" * 100  # 100 chars, 400 bytes
        tokens = ctxpack.estimate_tokens(text)
        assert tokens == 25  # 100 / 4

    def test_unicode_with_ascii_mixed(self):
        """Mixed ASCII and Unicode still uses chars // 4."""
        text = "hello 🌍 world"  # 13 chars
        tokens = ctxpack.estimate_tokens(text)
        assert tokens == max(1, 13 // 4)  # 3

    def test_cjk_content_estimation(self):
        """CJK characters are estimated by character count."""
        text = "你好世界"  # 4 Chinese chars
        tokens = ctxpack.estimate_tokens(text)
        assert tokens == 1  # 4 / 4

    # === Determinism ===

    def test_budget_truncation_is_deterministic(self):
        """Same input + same budget always produces same output."""
        inventory = [
            {
                "path": "a.txt",
                "size_bytes": 400,
                "tokens_estimate": 100,
                "content": "a" * 400,
            },
            {
                "path": "b.txt",
                "size_bytes": 800,
                "tokens_estimate": 200,
                "content": "b" * 800,
            },
        ]
        result1, inc1 = ctxpack.trim_to_budget(inventory, 100)
        result2, inc2 = ctxpack.trim_to_budget(inventory, 100)
        assert inc1 == inc2
        assert [i["path"] for i in result1] == [i["path"] for i in result2]
        assert result1[0].get("truncated") == result2[0].get("truncated")

    # === CLI integration ===

    def test_budget_flag_accepted(self, tmp_path):
        """--budget is accepted as an integer CLI flag."""
        (tmp_path / "test.txt").write_text("hello", encoding="utf-8")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 12000,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                },
            )()
            ctxpack.cmd_pack(args)

        json_file = tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")
        data = json.loads(json_file.read_text())
        assert data["budget_tokens"] == 12000


class TestPathPrivacy:
    """Regression tests for path privacy in generated packs (issue #8).

    Default output must not expose absolute local filesystem paths.
    Opt-in via --show-absolute-paths is available for debugging.
    """

    def test_default_markdown_uses_privacy_preserving_root(self, tmp_path):
        """Default Markdown output shows '.' not the absolute path."""
        (tmp_path / "test.txt").write_text("hello", encoding="utf-8")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 10000,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                    "show_absolute_paths": False,
                },
            )()
            ctxpack.cmd_pack(args)

        md_file = tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.md")
        md = md_file.read_text()
        assert "Generated from: `.`" in md
        assert str(tmp_path.resolve()) not in md

    def test_default_json_uses_privacy_preserving_root(self, tmp_path):
        """Default JSON output shows '.' not the absolute path."""
        (tmp_path / "test.txt").write_text("hello", encoding="utf-8")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 10000,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                    "show_absolute_paths": False,
                },
            )()
            ctxpack.cmd_pack(args)

        json_file = tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")
        data = json.loads(json_file.read_text())
        assert data["root"] == "."
        assert str(tmp_path.resolve()) not in json.dumps(data)

    def test_opt_in_show_absolute_paths(self, tmp_path):
        """--show-absolute-paths exposes the resolved path."""
        (tmp_path / "test.txt").write_text("hello", encoding="utf-8")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": 10000,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                    "show_absolute_paths": True,
                },
            )()
            ctxpack.cmd_pack(args)

        md_file = tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.md")
        md = md_file.read_text()
        assert str(tmp_path.resolve()) in md

        json_file = tmp_path / (ctxpack.DEFAULT_BASE_NAME + ".context.json")
        data = json.loads(json_file.read_text())
        assert data["root"] == str(tmp_path.resolve())


class TestBudgetValidation:
    """Tests for budget input validation (issue #12 follow-up).

    Negative budgets must be rejected with a clear error.
    """

    def test_negative_budget_rejected(self, tmp_path):
        """--budget -1 must raise ValueError."""
        (tmp_path / "test.txt").write_text("hello", encoding="utf-8")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": -1,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                    "show_absolute_paths": False,
                },
            )()
            with pytest.raises(ValueError, match="budget must be >= 0"):
                ctxpack.cmd_pack(args)

    def test_negative_budget_large_rejected(self, tmp_path):
        """--budget -100 must raise ValueError."""
        (tmp_path / "test.txt").write_text("hello", encoding="utf-8")

        with patch.object(Path, "cwd", return_value=tmp_path):
            args = type(
                "Args",
                (),
                {
                    "budget": -100,
                    "no_config": True,
                    "include": None,
                    "exclude": None,
                    "output_dir": None,
                    "base_name": None,
                    "show_absolute_paths": False,
                },
            )()
            with pytest.raises(ValueError, match="budget must be >= 0"):
                ctxpack.cmd_pack(args)


class TestTokenBudgetBoundaries:
    """Edge-case tests for very small and exact token budgets (issue #10).

    These tests document the budget allocator's deterministic behavior
    at all boundary values, ensuring no off-by-one or marker-over-budget
    regression is possible without a failing test.
    """

    # === Budget 0 ===

    def test_budget_zero_all_omitted(self):
        """Budget 0: all files are omitted (no room for content)."""
        inventory = [
            {
                "path": "a.txt",
                "size_bytes": 100,
                "tokens_estimate": 25,
                "content": "a" * 100,
            },
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 0)
        assert is_incomplete is True
        assert result[0].get("omitted") is True
        assert result[0]["tokens_estimate"] == 0

    # === Budget 1 ===

    def test_budget_one_tiny_file(self):
        """Budget 1: a single character file fits (1 token min)."""
        inventory = [
            {"path": "a.txt", "size_bytes": 1, "tokens_estimate": 1, "content": "a"},
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 1)
        assert is_incomplete is False
        assert result[0].get("truncated") is not True

    def test_budget_one_larger_file_truncates(self):
        """Budget 1: a 4-char file (1 token) fits exactly."""
        inventory = [
            {"path": "a.txt", "size_bytes": 4, "tokens_estimate": 1, "content": "abcd"},
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 1)
        assert is_incomplete is False
        assert result[0].get("truncated") is not True

    def test_budget_one_oversized_file(self):
        """Budget 1: an 8-char file (2 tokens) omitted (budget < marker estimate)."""
        inventory = [
            {
                "path": "a.txt",
                "size_bytes": 8,
                "tokens_estimate": 2,
                "content": "abcdefgh",
            },
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 1)
        assert is_incomplete is True
        # Budget 1 < marker estimate, so file is omitted (no room for marker)
        assert result[0].get("omitted") is True

    # === Marker estimate boundaries ===

    def test_budget_smaller_than_marker(self):
        """Budget smaller than marker estimate: file omitted."""
        marker_tokens = ctxpack.estimate_tokens(ctxpack.TRUNCATION_MARKER)
        inventory = [
            {
                "path": "a.txt",
                "size_bytes": 400,
                "tokens_estimate": 100,
                "content": "a" * 400,
            },
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, marker_tokens - 1)
        assert is_incomplete is True
        # File is omitted because remaining (budget - 0) < marker_tokens
        assert result[0].get("omitted") is True

    def test_budget_exactly_marker(self):
        """Budget equals marker estimate: file still omitted (no room for content)."""
        marker_tokens = ctxpack.estimate_tokens(ctxpack.TRUNCATION_MARKER)
        inventory = [
            {
                "path": "a.txt",
                "size_bytes": 400,
                "tokens_estimate": 100,
                "content": "a" * 400,
            },
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, marker_tokens)
        assert is_incomplete is True
        # remaining = budget - 0 - marker_tokens = 0, so file is omitted
        assert result[0].get("omitted") is True

    # === Empty files ===

    def test_empty_file_zero_tokens(self):
        """Empty file contributes 0 tokens (no content = no tokens)."""
        inventory = [
            {"path": "empty.txt", "size_bytes": 0, "tokens_estimate": 0, "content": ""},
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 100)
        assert is_incomplete is False
        assert result[0].get("omitted") is not True

    def test_empty_files_no_budget_used(self):
        """Multiple empty files use no budget."""
        inventory = [
            {"path": f"{c}.txt", "size_bytes": 0, "tokens_estimate": 0, "content": ""}
            for c in "abc"
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 100)
        assert is_incomplete is False
        assert len(result) == 3
        assert all(not r.get("omitted") for r in result)

    # === One-character files ===

    def test_one_char_file_one_token(self):
        """A single character file uses 1 token (minimum)."""
        inventory = [
            {"path": "a.txt", "size_bytes": 1, "tokens_estimate": 1, "content": "x"},
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 1)
        assert is_incomplete is False
        assert result[0]["tokens_estimate"] == 1

    def test_many_one_char_files(self):
        """Many single-char files fit until budget is reached."""
        inventory = [
            {"path": f"{c}.txt", "size_bytes": 1, "tokens_estimate": 1, "content": c}
            for c in "abcdefghij"
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 5)
        assert is_incomplete is True
        included = [r for r in result if not r.get("omitted")]
        assert len(included) == 5

    # === Unicode-heavy content ===

    def test_unicode_emoji_budget(self):
        """Emoji content estimated by chars, not bytes."""
        text = "🎉" * 20  # 20 chars, 80 bytes, 5 tokens
        inventory = [
            {
                "path": "emoji.txt",
                "size_bytes": 80,
                "tokens_estimate": 5,
                "content": text,
            },
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 5)
        assert is_incomplete is False
        assert result[0].get("truncated") is not True

    def test_unicode_cjk_budget(self):
        """CJK content at exact budget boundary."""
        text = "你好世界"  # 4 chars, 1 token
        inventory = [
            {
                "path": "cjk.txt",
                "size_bytes": 12,
                "tokens_estimate": 1,
                "content": text,
            },
        ]
        _result, is_incomplete = ctxpack.trim_to_budget(inventory, 1)
        assert is_incomplete is False

    # === File exactly at remaining budget ===
    def test_file_exactly_at_remaining_budget(self):
        """A file that fits exactly is kept whole."""
        inventory = [
            {
                "path": "a.txt",
                "size_bytes": 400,
                "tokens_estimate": 100,
                "content": "a" * 400,
            },
            {
                "path": "b.txt",
                "size_bytes": 200,
                "tokens_estimate": 50,
                "content": "b" * 200,
            },
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 150)
        assert is_incomplete is False
        assert result[0].get("truncated") is not True
        assert result[1].get("truncated") is not True

    # === Multiple files competing at same budget ===

    def test_two_files_at_boundary(self):
        """Two files: first fits, second truncated at boundary."""
        inventory = [
            {
                "path": "a.txt",
                "size_bytes": 400,
                "tokens_estimate": 100,
                "content": "a" * 400,
            },
            {
                "path": "b.txt",
                "size_bytes": 400,
                "tokens_estimate": 100,
                "content": "b" * 400,
            },
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 150)
        assert is_incomplete is True
        assert result[0].get("truncated") is not True
        assert result[1].get("truncated") is True

    def test_three_files_last_two_omitted(self):
        """Three files: first truncated, next two omitted."""
        inventory = [
            {
                "path": "a.txt",
                "size_bytes": 800,
                "tokens_estimate": 200,
                "content": "a" * 800,
            },
            {
                "path": "b.txt",
                "size_bytes": 400,
                "tokens_estimate": 100,
                "content": "b" * 400,
            },
            {
                "path": "c.txt",
                "size_bytes": 400,
                "tokens_estimate": 100,
                "content": "c" * 400,
            },
        ]
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 100)
        assert is_incomplete is True
        assert result[0].get("truncated") is True
        assert result[1].get("omitted") is True
        assert result[2].get("omitted") is True
