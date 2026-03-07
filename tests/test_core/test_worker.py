"""Tests for core/worker.py — in-process VTK pipeline execution."""

from __future__ import annotations

from pathlib import Path

import pytest

from viznoir.core.worker import InProcessExecutor


class TestInProcessExecutor:
    def test_execute_simple_script(self):
        executor = InProcessExecutor()
        script = (
            "import json, os\n"
            "out = os.environ['VIZNOIR_OUTPUT_DIR']\n"
            "with open(os.path.join(out, 'result.json'), 'w') as f:\n"
            "    json.dump({'status': 'ok'}, f)\n"
        )
        result = executor.run(script)
        assert result.exit_code == 0
        assert "result.json" in result.output_file_data

    def test_execute_script_with_error(self):
        executor = InProcessExecutor()
        script = "raise RuntimeError('boom')"
        result = executor.run(script)
        assert result.exit_code != 0
        assert "boom" in result.stderr

    def test_captures_stdout(self):
        executor = InProcessExecutor()
        script = "print('hello from worker')"
        result = executor.run(script)
        assert "hello from worker" in result.stdout

    def test_output_dir_set_in_env(self):
        executor = InProcessExecutor()
        script = (
            "import os\n"
            "out = os.environ['VIZNOIR_OUTPUT_DIR']\n"
            "assert os.path.isdir(out)\n"
            "with open(os.path.join(out, 'test.txt'), 'w') as f:\n"
            "    f.write('ok')\n"
        )
        result = executor.run(script)
        assert result.exit_code == 0
        assert "test.txt" in result.output_file_data

    def test_isolation_between_runs(self):
        executor = InProcessExecutor()
        script1 = (
            "import os\n"
            "with open(os.path.join(os.environ['VIZNOIR_OUTPUT_DIR'], 'a.txt'), 'w') as f:\n"
            "    f.write('a')\n"
        )
        script2 = (
            "import os\n"
            "with open(os.path.join(os.environ['VIZNOIR_OUTPUT_DIR'], 'b.txt'), 'w') as f:\n"
            "    f.write('b')\n"
        )
        r1 = executor.run(script1)
        r2 = executor.run(script2)
        assert "a.txt" in r1.output_file_data
        assert "b.txt" in r2.output_file_data
        assert "a.txt" not in r2.output_file_data


class TestVTKRunnerInProcess:
    @pytest.mark.asyncio
    async def test_local_mode_uses_inprocess(self):
        from viznoir.config import PVConfig
        from viznoir.core.runner import VTKRunner

        config = PVConfig(output_dir=Path("/tmp/viznoir-test"))
        runner = VTKRunner(config=config, mode="local")

        script = (
            "import json, os\n"
            "out = os.environ['VIZNOIR_OUTPUT_DIR']\n"
            "with open(os.path.join(out, 'result.json'), 'w') as f:\n"
            "    json.dump({'answer': 42}, f)\n"
        )
        result = await runner.execute(script)
        assert result.ok
        assert result.json_result == {"answer": 42}
