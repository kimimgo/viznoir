"""Tests for server-level input validation."""

from __future__ import annotations

import pytest


class TestValidateFilePath:
    """Test _validate_file_path path traversal prevention."""

    def test_valid_path_within_data_dir(self):
        from parapilot.server import _validate_file_path

        result = _validate_file_path("/data/cavity.vtk")
        assert result == "/data/cavity.vtk"

    def test_valid_nested_path(self):
        from parapilot.server import _validate_file_path

        result = _validate_file_path("/data/cases/foam/cavity.foam")
        assert result == "/data/cases/foam/cavity.foam"

    def test_rejects_path_traversal(self):
        from parapilot.server import _validate_file_path

        with pytest.raises(ValueError, match="Access denied"):
            _validate_file_path("/etc/shadow")

    def test_rejects_dotdot_traversal(self):
        from parapilot.server import _validate_file_path

        with pytest.raises(ValueError, match="Access denied"):
            _validate_file_path("/data/../etc/passwd")

    def test_rejects_absolute_outside(self):
        from parapilot.server import _validate_file_path

        with pytest.raises(ValueError, match="Access denied"):
            _validate_file_path("/home/user/.ssh/id_rsa")

    def test_data_dir_itself_is_allowed(self):
        from parapilot.server import _validate_file_path

        # data_dir itself should be allowed (e.g., listing)
        result = _validate_file_path("/data")
        assert result == "/data"
