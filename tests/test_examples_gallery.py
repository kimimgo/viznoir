"""Tests for examples/ gallery structure and content.

Verifies that all example README files exist, are well-formed,
and contain the expected sections and tool call JSON blocks.
"""

import json
import re
from pathlib import Path

import pytest

EXAMPLES_ROOT = Path(__file__).parent.parent / "examples"

EXPECTED_FILES = [
    EXAMPLES_ROOT / "README.md",
    EXAMPLES_ROOT / "01-cfd-pressure" / "README.md",
    EXAMPLES_ROOT / "02-fea-displacement" / "README.md",
    EXAMPLES_ROOT / "03-thermal-analysis" / "README.md",
    EXAMPLES_ROOT / "04-medical-imaging" / "README.md",
    EXAMPLES_ROOT / "05-openfoam-cavity" / "README.md",
]

EXAMPLE_DIRS = [
    "01-cfd-pressure",
    "02-fea-displacement",
    "03-thermal-analysis",
    "04-medical-imaging",
    "05-openfoam-cavity",
]

# Tools that must appear in each example
REQUIRED_TOOLS_PER_EXAMPLE = {
    "01-cfd-pressure": ["inspect_data", "render", "slice", "streamlines", "extract_stats"],
    "02-fea-displacement": ["inspect_data", "render", "contour"],
    "03-thermal-analysis": ["inspect_data", "volume_render", "slice", "plot_over_line"],
    "04-medical-imaging": ["inspect_data", "volume_render", "clip", "cinematic_render"],
    "05-openfoam-cavity": ["inspect_data", "inspect_physics", "render", "animate", "split_animate"],
}


class TestGalleryStructure:
    """All required files and directories exist."""

    def test_gallery_root_readme_exists(self):
        assert EXAMPLES_ROOT.is_dir(), "examples/ directory must exist"
        readme = EXAMPLES_ROOT / "README.md"
        assert readme.exists(), f"{readme} must exist"

    @pytest.mark.parametrize("subdir", EXAMPLE_DIRS)
    def test_example_directory_exists(self, subdir):
        d = EXAMPLES_ROOT / subdir
        assert d.is_dir(), f"examples/{subdir}/ directory must exist"

    @pytest.mark.parametrize("subdir", EXAMPLE_DIRS)
    def test_example_readme_exists(self, subdir):
        readme = EXAMPLES_ROOT / subdir / "README.md"
        assert readme.exists(), f"examples/{subdir}/README.md must exist"

    def test_all_expected_files_exist(self):
        missing = [str(f) for f in EXPECTED_FILES if not f.exists()]
        assert not missing, f"Missing files: {missing}"


class TestGalleryRootReadme:
    """examples/README.md content validation."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = (EXAMPLES_ROOT / "README.md").read_text(encoding="utf-8")

    def test_has_title(self):
        assert self.content.startswith("#"), "README must start with a markdown heading"

    def test_mentions_viznoir(self):
        assert "viznoir" in self.content.lower(), "README must mention viznoir"

    def test_has_table_of_contents(self):
        # Should reference all 5 examples
        for subdir in EXAMPLE_DIRS:
            assert subdir in self.content, f"TOC must reference {subdir}"

    def test_lists_all_domains(self):
        domains = ["CFD", "FEA", "Thermal", "Medical", "OpenFOAM"]
        for domain in domains:
            assert domain in self.content, f"README must mention domain: {domain}"

    def test_mentions_mcp_tools(self):
        assert "MCP" in self.content, "README must mention MCP tools"

    def test_line_count_reasonable(self):
        lines = self.content.splitlines()
        assert 20 <= len(lines) <= 120, f"Root README should be 20-120 lines, got {len(lines)}"


class TestExampleReadmes:
    """Individual example README validation."""

    def _load(self, subdir: str) -> str:
        return (EXAMPLES_ROOT / subdir / "README.md").read_text(encoding="utf-8")

    def _extract_json_blocks(self, content: str) -> list[dict]:
        """Extract all ```json ... ``` code blocks and parse them."""
        pattern = r"```json\s*\n(.*?)\n```"
        blocks = re.findall(pattern, content, re.DOTALL)
        parsed = []
        for block in blocks:
            try:
                parsed.append(json.loads(block))
            except json.JSONDecodeError:
                pass
        return parsed

    @pytest.mark.parametrize("subdir", EXAMPLE_DIRS)
    def test_has_h1_title(self, subdir):
        content = self._load(subdir)
        lines = content.splitlines()
        h1_lines = [line for line in lines if line.startswith("# ")]
        assert h1_lines, f"{subdir}/README.md must have an H1 title"

    @pytest.mark.parametrize("subdir", EXAMPLE_DIRS)
    def test_has_json_tool_calls(self, subdir):
        content = self._load(subdir)
        blocks = self._extract_json_blocks(content)
        assert blocks, f"{subdir}/README.md must contain at least one ```json``` block"

    @pytest.mark.parametrize("subdir", EXAMPLE_DIRS)
    def test_json_blocks_have_tool_field(self, subdir):
        content = self._load(subdir)
        blocks = self._extract_json_blocks(content)
        for block in blocks:
            if "tool" in block:
                assert "arguments" in block, f"{subdir}: JSON block with 'tool' must also have 'arguments'"

    @pytest.mark.parametrize("subdir,required_tools", REQUIRED_TOOLS_PER_EXAMPLE.items())
    def test_required_tools_mentioned(self, subdir, required_tools):
        content = self._load(subdir)
        for tool in required_tools:
            assert tool in content, f"{subdir}/README.md must mention tool: {tool}"

    @pytest.mark.parametrize("subdir", EXAMPLE_DIRS)
    def test_line_count_reasonable(self, subdir):
        content = self._load(subdir)
        lines = content.splitlines()
        assert 40 <= len(lines) <= 150, f"{subdir}/README.md should be 40-150 lines, got {len(lines)}"

    @pytest.mark.parametrize("subdir", EXAMPLE_DIRS)
    def test_has_overview_section(self, subdir):
        content = self._load(subdir)
        assert "##" in content, f"{subdir}/README.md must have at least one section (##)"

    def test_cfd_mentions_pressure_and_velocity(self):
        content = self._load("01-cfd-pressure")
        assert "pressure" in content.lower()
        assert "velocity" in content.lower() or "U" in content

    def test_fea_mentions_stress(self):
        content = self._load("02-fea-displacement")
        assert "stress" in content.lower() or "vonMises" in content

    def test_thermal_mentions_temperature(self):
        content = self._load("03-thermal-analysis")
        assert "temperature" in content.lower() or '"T"' in content

    def test_medical_mentions_volume_or_ct(self):
        content = self._load("04-medical-imaging")
        assert "CT" in content or "MRI" in content or "volume" in content.lower()

    def test_openfoam_references_cavity_fixture(self):
        content = self._load("05-openfoam-cavity")
        assert "cavity" in content.lower()
        assert "case.foam" in content or "foam" in content.lower()

    def test_openfoam_mentions_viznoir_resource(self):
        content = self._load("05-openfoam-cavity")
        assert "viznoir://" in content

    def test_examples_use_english_only(self):
        """No Korean characters in example files (public repo)."""
        import unicodedata

        for subdir in EXAMPLE_DIRS:
            content = self._load(subdir)
            for char in content:
                unicodedata.category(char)
                name = unicodedata.name(char, "")
                assert "CJK" not in name and "HANGUL" not in name, (
                    f"{subdir}/README.md contains non-English character: {repr(char)}"
                )
        root_content = (EXAMPLES_ROOT / "README.md").read_text(encoding="utf-8")
        for char in root_content:
            name = unicodedata.name(char, "")
            assert "CJK" not in name and "HANGUL" not in name, (
                f"examples/README.md contains non-English character: {repr(char)}"
            )
