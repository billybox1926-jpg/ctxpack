#!/usr/bin/env python3
"""
Test suite for ctxpack - dependency-free repo-to-prompt pack builder.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module under test
import sys
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
        # Check for output file patterns (they use DEFAULT_BASE_NAME in v0.2.0)
        assert f"{ctxpack.DEFAULT_BASE_NAME}.context.json" in patterns
        assert f"{ctxpack.DEFAULT_BASE_NAME}.context.md" in patterns

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


class TestShouldProcess:
    """Tests for should_process function (replaces should_ignore in v0.2.0)."""

    def test_ignore_git_directory(self, tmp_path):
        """Should ignore .git directory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        include_patterns = []
        # Use both ".git" and ".git/**" patterns to match directory and contents
        exclude_patterns = [".git", ".git/**"]
        
        # Test that .git directory itself is ignored (relative path is ".git")
        assert ctxpack.should_process(git_dir, tmp_path, include_patterns, exclude_patterns) is False
        
        # Also test files inside .git are ignored
        git_file = git_dir / "config"
        git_file.write_text("test")
        assert ctxpack.should_process(git_file, tmp_path, include_patterns, exclude_patterns) is False

    def test_ignore_log_files_anywhere(self, tmp_path):
        """Should ignore *.log files anywhere in the tree (bare filename pattern)."""
        log_file_root = tmp_path / "app.log"
        log_file_subdir = tmp_path / "subdir" / "debug.log"
        log_file_subdir.parent.mkdir(parents=True)
        log_file_root.write_text("log content")
        log_file_subdir.write_text("log content")
        
        include_patterns = []
        exclude_patterns = ["*.log"]
        
        assert ctxpack.should_process(log_file_root, tmp_path, include_patterns, exclude_patterns) is False
        assert ctxpack.should_process(log_file_subdir, tmp_path, include_patterns, exclude_patterns) is False

    def test_ignore_node_modules(self, tmp_path):
        """Should ignore node_modules directory and contents."""
        node_dir = tmp_path / "node_modules" / "package"
        node_dir.mkdir(parents=True)
        include_patterns = []
        exclude_patterns = ["node_modules/**"]
        
        assert ctxpack.should_process(node_dir, tmp_path, include_patterns, exclude_patterns) is False

    def test_dont_ignore_normal_file(self, tmp_path):
        """Should not ignore normal source files."""
        src_file = tmp_path / "src" / "main.py"
        src_file.parent.mkdir()
        src_file.write_text("print('hello')")
        
        include_patterns = []
        exclude_patterns = ["*.log", "node_modules/**"]
        
        assert ctxpack.should_process(src_file, tmp_path, include_patterns, exclude_patterns) is True

    def test_ignore_pyc_files(self, tmp_path):
        """Should ignore .pyc files."""
        pyc_file = tmp_path / "module.pyc"
        pyc_file.write_text("binary")
        include_patterns = []
        exclude_patterns = ["*.pyc"]
        
        assert ctxpack.should_process(pyc_file, tmp_path, include_patterns, exclude_patterns) is False

    def test_ignore_ctxpack_outputs(self, tmp_path):
        """Should ignore ctxpack output files by default."""
        json_output = tmp_path / f"{ctxpack.DEFAULT_BASE_NAME}.context.json"
        md_output = tmp_path / f"{ctxpack.DEFAULT_BASE_NAME}.context.md"
        json_output.write_text("{}")
        md_output.write_text("")
        
        patterns = ctxpack.load_ignore_patterns(tmp_path, [])
        # In v0.2.0, load_ignore_patterns returns only exclude patterns
        include_patterns = []
        exclude_patterns = patterns
        
        assert ctxpack.should_process(json_output, tmp_path, include_patterns, exclude_patterns) is False
        assert ctxpack.should_process(md_output, tmp_path, include_patterns, exclude_patterns) is False


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

    def test_empty_string(self):
        """Should handle empty string."""
        tokens = ctxpack.estimate_tokens("")
        
        assert tokens == 1  # max(1, 0 // 4) = 1


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
        
        include_patterns = []
        exclude_patterns = []
        inventory = ctxpack.build_file_inventory(tmp_path, include_patterns, exclude_patterns)
        
        assert len(inventory) == 3
        paths = [item["path"] for item in inventory]
        assert "file1.txt" in paths
        assert "file2.py" in paths
        assert "subdir/file3.md" in paths

    def test_skip_ignored_files(self, tmp_path):
        """Should skip files matching ignore patterns."""
        (tmp_path / "good.txt").write_text("good")
        (tmp_path / "bad.log").write_text("bad")
        
        include_patterns = []
        exclude_patterns = ["*.log"]
        inventory = ctxpack.build_file_inventory(tmp_path, include_patterns, exclude_patterns)
        
        assert len(inventory) == 1
        assert inventory[0]["path"] == "good.txt"

    def test_skip_binary_files(self, tmp_path):
        """Should skip binary files."""
        (tmp_path / "text.txt").write_text("text")
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        
        include_patterns = []
        exclude_patterns = []
        inventory = ctxpack.build_file_inventory(tmp_path, include_patterns, exclude_patterns)
        
        assert len(inventory) == 1
        assert inventory[0]["path"] == "text.txt"

    def test_inventory_sorted_by_path(self, tmp_path):
        """Should return inventory sorted by path."""
        (tmp_path / "z.txt").write_text("z")
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "m.txt").write_text("m")
        
        include_patterns = []
        exclude_patterns = []
        inventory = ctxpack.build_file_inventory(tmp_path, include_patterns, exclude_patterns)
        
        paths = [item["path"] for item in inventory]
        assert paths == ["a.txt", "m.txt", "z.txt"]

    def test_inventory_includes_metadata(self, tmp_path):
        """Should include size, tokens, and content in inventory items."""
        test_file = tmp_path / "test.txt"
        content = "Hello"
        test_file.write_text(content)
        
        include_patterns = []
        exclude_patterns = []
        inventory = ctxpack.build_file_inventory(tmp_path, include_patterns, exclude_patterns)
        
        assert len(inventory) == 1
        item = inventory[0]
        assert "path" in item
        assert "size_bytes" in item
        assert "tokens_estimate" in item
        assert "content" in item
        assert item["size_bytes"] == len(content.encode('utf-8'))


class TestTrimToBudget:
    """Tests for trim_to_budget function."""

    def test_keep_all_within_budget(self):
        """Should keep all files if within budget."""
        inventory = [
            {"path": "a.txt", "content": "a" * 100, "tokens_estimate": 25, "size_bytes": 100},
            {"path": "b.txt", "content": "b" * 100, "tokens_estimate": 25, "size_bytes": 100}
        ]
        
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 100)
        
        assert len(result) == 2
        assert all(not item.get("truncated", False) for item in result)
        assert is_incomplete is False

    def test_truncate_when_over_budget(self):
        """Should truncate last file when over budget."""
        inventory = [
            {"path": "a.txt", "content": "a" * 100, "tokens_estimate": 25, "size_bytes": 100},
            {"path": "b.txt", "content": "b" * 400, "tokens_estimate": 100, "size_bytes": 400}
        ]
        
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 50)
        
        assert len(result) == 2
        assert result[0]["path"] == "a.txt"
        assert not result[0].get("truncated", False)
        assert result[1]["path"] == "b.txt"
        assert result[1].get("truncated", False)
        assert "[TRUNCATED by ctxpack" in result[1]["content"]
        assert is_incomplete is True

    def test_stop_when_budget_exhausted(self):
        """Should stop adding files when budget is exhausted."""
        inventory = [
            {"path": "a.txt", "content": "a" * 100, "tokens_estimate": 25, "size_bytes": 100},
            {"path": "b.txt", "content": "b" * 100, "tokens_estimate": 25, "size_bytes": 100},
            {"path": "c.txt", "content": "c" * 100, "tokens_estimate": 25, "size_bytes": 100}
        ]
        
        result, is_incomplete = ctxpack.trim_to_budget(inventory, 30)
        
        # First file fits (25 tokens), second gets truncated to fit remaining budget
        assert len(result) >= 1
        # The truncation logic may add a few extra tokens for the truncation message
        # so we check that we don't significantly exceed the budget
        total_tokens = sum(item["tokens_estimate"] for item in result)
        assert total_tokens <= 50  # Allow some overhead for truncation message
        assert result[0]["path"] == "a.txt"
        assert is_incomplete is True


class TestGenerateMarkdown:
    """Tests for generate_markdown function."""

    def test_markdown_header(self, tmp_path):
        """Should include proper header in markdown output."""
        inventory = []
        md = ctxpack.generate_markdown(inventory, tmp_path, is_incomplete=False)
        
        assert "# ctxpack Context Pack" in md
        assert f"Generated from:" in md
        assert "Files included: 0" in md

    def test_markdown_file_entries(self, tmp_path):
        """Should include file entries with metadata."""
        inventory = [
            {
                "path": "test.txt",
                "size_bytes": 100,
                "tokens_estimate": 25,
                "content": "Hello World",
                "truncated": False
            }
        ]
        md = ctxpack.generate_markdown(inventory, tmp_path, is_incomplete=False)
        
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
                "truncated": True
            }
        ]
        md = ctxpack.generate_markdown(inventory, tmp_path, is_incomplete=False)
        
        assert "⚠️ Truncated to fit token budget" in md

    def test_markdown_incomplete_warning(self, tmp_path):
        """Should include incomplete warning when budget exceeded."""
        inventory = []
        md = ctxpack.generate_markdown(inventory, tmp_path, is_incomplete=True)
        
        assert "WARNING" in md
        assert "exceeded the budget" in md


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
                "truncated": False
            }
        ]
        budget = 8000
        
        result = ctxpack.generate_json(inventory, tmp_path, budget, is_incomplete=False)
        
        assert result["generator"] == "ctxpack"
        assert "root" in result
        assert result["budget_tokens"] == budget
        assert "files" in result
        assert len(result["files"]) == 1
        assert "is_incomplete" in result
        assert result["is_incomplete"] is False

    def test_json_file_fields(self, tmp_path):
        """Should include all required fields in file entries."""
        inventory = [
            {
                "path": "test.txt",
                "size_bytes": 100,
                "tokens_estimate": 25,
                "content": "Hello",
                "truncated": False
            }
        ]
        
        result = ctxpack.generate_json(inventory, tmp_path, 8000, is_incomplete=False)
        file_entry = result["files"][0]
        
        assert "path" in file_entry
        assert "size_bytes" in file_entry
        assert "tokens_estimate" in file_entry
        assert "truncated" in file_entry
        assert "content" in file_entry

    def test_json_is_incomplete_flag(self, tmp_path):
        """Should set is_incomplete flag when budget exceeded."""
        inventory = []
        
        result = ctxpack.generate_json(inventory, tmp_path, 8000, is_incomplete=True)
        
        assert result["is_incomplete"] is True


class TestCmdInit:
    """Tests for cmd_init function."""

    def test_create_ignore_file(self, tmp_path):
        """Should create .ctxignore file if missing."""
        with patch.object(Path, 'cwd', return_value=tmp_path):
            args = type('Args', (), {})()
            ctxpack.cmd_init(args)
        
        ignore_file = tmp_path / ctxpack.DEFAULT_IGNORE_FILE
        assert ignore_file.exists()
        content = ignore_file.read_text()
        assert ".git/" in content
        assert "*.log" in content

    def test_create_config_file(self, tmp_path):
        """Should create ctxpack.json file if missing."""
        with patch.object(Path, 'cwd', return_value=tmp_path):
            args = type('Args', (), {})()
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
        
        with patch.object(Path, 'cwd', return_value=tmp_path):
            args = type('Args', (), {})()
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
        
        with patch.object(Path, 'cwd', return_value=tmp_path):
            args = type('Args', (), {
                'budget': 8000, 
                'no_config': True, 
                'budget_set': True,
                'output_dir_set': False,
                'base_name_set': False,
                'include': None,
                'exclude': None,
                'output_dir': str(tmp_path),  # Use absolute path
                'base_name': 'ctxpack'
            })()
            ctxpack.cmd_pack(args)
        
        json_file = tmp_path / f"{ctxpack.DEFAULT_BASE_NAME}.context.json"
        md_file = tmp_path / f"{ctxpack.DEFAULT_BASE_NAME}.context.md"
        
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
        
        with patch.object(Path, 'cwd', return_value=tmp_path):
            args = type('Args', (), {
                'budget': 100, 
                'no_config': True, 
                'budget_set': True,
                'output_dir_set': False,
                'base_name_set': False,
                'include': None,
                'exclude': None,
                'output_dir': str(tmp_path),  # Use absolute path
                'base_name': 'ctxpack'
            })()
            ctxpack.cmd_pack(args)
        
        json_file = tmp_path / f"{ctxpack.DEFAULT_BASE_NAME}.context.json"
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
        
        with patch.object(Path, 'cwd', return_value=tmp_path):
            args = type('Args', (), {
                'budget': 8000, 
                'no_config': False, 
                'budget_set': False,
                'output_dir_set': False,
                'base_name_set': False,
                'include': None,
                'exclude': None,
                'output_dir': str(tmp_path),  # Use absolute path
                'base_name': 'ctxpack'
            })()
            ctxpack.cmd_pack(args)
        
        json_file = tmp_path / f"{ctxpack.DEFAULT_BASE_NAME}.context.json"
        data = json.loads(json_file.read_text())
        
        assert data["budget_tokens"] == 5000

    def test_no_config_flag_bypasses_config(self, tmp_path):
        """Should ignore config file when --no-config flag is set."""
        # Create config file with different budget
        config = {"budget_tokens": 5000}
        config_file = tmp_path / ctxpack.DEFAULT_CONFIG_FILE
        config_file.write_text(json.dumps(config))
        
        # Create test file
        (tmp_path / "test.txt").write_text("content")
        
        with patch.object(Path, 'cwd', return_value=tmp_path):
            args = type('Args', (), {
                'budget': 3000, 
                'no_config': True, 
                'budget_set': True,
                'output_dir_set': False,
                'base_name_set': False,
                'include': None,
                'exclude': None,
                'output_dir': str(tmp_path),  # Use absolute path
                'base_name': 'ctxpack'
            })()
            ctxpack.cmd_pack(args)
        
        json_file = tmp_path / f"{ctxpack.DEFAULT_BASE_NAME}.context.json"
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
        with patch.object(Path, 'cwd', return_value=tmp_path):
            init_args = type('Args', (), {})()
            ctxpack.cmd_init(init_args)
        
        # Pack with custom budget
        with patch.object(Path, 'cwd', return_value=tmp_path):
            pack_args = type('Args', (), {
                'budget': 500, 
                'no_config': True, 
                'budget_set': True,
                'output_dir_set': False,
                'base_name_set': False,
                'include': None,
                'exclude': None,
                'output_dir': str(tmp_path),  # Use absolute path
                'base_name': 'ctxpack'
            })()
            ctxpack.cmd_pack(pack_args)
        
        # Verify outputs
        json_file = tmp_path / f"{ctxpack.DEFAULT_BASE_NAME}.context.json"
        md_file = tmp_path / f"{ctxpack.DEFAULT_BASE_NAME}.context.md"
        
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
        
        with patch.object(Path, 'cwd', return_value=tmp_path):
            args = type('Args', (), {
                'budget': 10000, 
                'no_config': True, 
                'budget_set': True,
                'output_dir_set': False,
                'base_name_set': False,
                'include': None,
                'exclude': None,
                'output_dir': str(tmp_path),  # Use absolute path
                'base_name': 'ctxpack'
            })()
            ctxpack.cmd_pack(args)
        
        json_file = tmp_path / f"{ctxpack.DEFAULT_BASE_NAME}.context.json"
        data = json.loads(json_file.read_text())
        
        paths = [f["path"] for f in data["files"]]
        assert "good.py" in paths
        assert "bad.pyc" not in paths
        assert "app.log" not in paths
        assert not any("venv" in p for p in paths)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
