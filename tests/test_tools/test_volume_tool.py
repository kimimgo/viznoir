"""Tests for volume_render MCP tool."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestVolumeRenderImpl:
    @pytest.mark.asyncio
    @patch("viznoir.tools.volume.cinematic_render_impl")
    async def test_calls_cinematic(self, mock_cine):
        from viznoir.tools.volume import volume_render_impl

        mock_cine.return_value = b"fake-png"
        runner = MagicMock()

        result = await volume_render_impl(
            file_path="/data/head.vti",
            runner=runner,
            field_name="scalars",
            transfer_preset="ct_bone",
        )
        assert result == b"fake-png"
        mock_cine.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_preset_raises(self):
        from viznoir.tools.volume import volume_render_impl

        runner = MagicMock()
        with pytest.raises(KeyError, match="no_such"):
            await volume_render_impl(
                file_path="/data/head.vti",
                runner=runner,
                transfer_preset="no_such",
            )
