"""Unit tests for the knowledge cache library."""

import json
import tempfile
import sys
sys.path.insert(0, "data-plane")

from agent_runner.knowledge import KnowledgeCache


def test_write_and_read_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = KnowledgeCache(tmpdir)
        cache.write_file("test/hello.txt", "Hello, world!")
        content = cache.read_file("test/hello.txt")
        assert content == "Hello, world!"


def test_write_and_read_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = KnowledgeCache(tmpdir)
        data = {"key": "value", "number": 42}
        cache.write_json("test/data.json", data)
        result = cache.read_json("test/data.json")
        assert result == data


def test_list_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = KnowledgeCache(tmpdir)
        cache.write_file("dir/a.txt", "a")
        cache.write_file("dir/b.txt", "b")
        cache.write_file("dir/c.json", "c")
        txt_files = cache.list_files("dir", "*.txt")
        assert len(txt_files) == 2
        all_files = cache.list_files("dir")
        assert len(all_files) == 3


def test_file_exists():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = KnowledgeCache(tmpdir)
        assert not cache.file_exists("nope.txt")
        cache.write_file("exists.txt", "yes")
        assert cache.file_exists("exists.txt")


def test_commit():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = KnowledgeCache(tmpdir)
        cache.write_file("test.txt", "data")
        commit_hash = cache.commit(
            message="test commit",
            files=["test.txt"],
            agent_name="test-agent",
            job_id=1,
        )
        assert len(commit_hash) == 40  # Full SHA


def test_list_empty_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = KnowledgeCache(tmpdir)
        assert cache.list_files("nonexistent") == []


if __name__ == "__main__":
    test_write_and_read_file()
    test_write_and_read_json()
    test_list_files()
    test_file_exists()
    test_commit()
    test_list_empty_dir()
    print("All knowledge cache tests passed!")
