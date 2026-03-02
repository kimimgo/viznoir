"""MCP Resource registration — formats, filters, presets, pipeline examples."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from parapilot.core.registry import FILTER_REGISTRY, FORMAT_REGISTRY
from parapilot.presets.registry import CASE_PRESETS, COLORMAP_GUIDE, REPRESENTATION_GUIDE

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_resources(mcp: FastMCP) -> None:
    """Register all MCP resources."""

    @mcp.resource("parapilot://formats")
    def formats_resource() -> str:
        """Supported file formats with reader mappings."""
        data = {
            ext: {"reader": reader, "description": _format_desc(ext)}
            for ext, reader in sorted(FORMAT_REGISTRY.items())
        }
        return json.dumps(data, indent=2)

    @mcp.resource("parapilot://filters")
    def filters_resource() -> str:
        """All available filters with parameter schemas and usage examples."""
        data = {}
        for name, schema in sorted(FILTER_REGISTRY.items()):
            data[name] = {
                "vtk_class": schema["vtk_class"],
                "params": schema["params"],
            }
        return json.dumps(data, indent=2)

    @mcp.resource("parapilot://colormaps")
    def colormaps_resource() -> str:
        """Color map presets and recommended usage per field type."""
        return json.dumps(COLORMAP_GUIDE, indent=2)

    @mcp.resource("parapilot://representations")
    def representations_resource() -> str:
        """Available representation types and when to use each."""
        return json.dumps(REPRESENTATION_GUIDE, indent=2)

    @mcp.resource("parapilot://case-presets")
    def case_presets_resource() -> str:
        """Rendering presets for simulation case types.

        Each preset defines recommended cameras, fields, colormaps,
        representations, and common filter chains for a domain:
        external_aero, internal_flow, multiphase, thermal, structural_fea, sph_particles.
        """
        return json.dumps(CASE_PRESETS, indent=2)

    @mcp.resource("parapilot://cameras")
    def cameras_resource() -> str:
        """Camera presets and custom configuration guide."""
        cameras = {
            "presets": {
                "isometric": "3D diagonal view (default)",
                "top": "Top-down view (XY plane)",
                "front": "Front view (XZ plane)",
                "right": "Right side view (YZ plane)",
                "left": "Left side view (YZ plane, reversed)",
                "back": "Back view (XZ plane, reversed)",
            },
            "custom": {
                "position": "[x, y, z] — camera location",
                "focal_point": "[x, y, z] — look-at point",
                "view_up": "[x, y, z] — up direction vector",
                "zoom": "float — zoom factor (>1 closer, <1 farther)",
            },
        }
        return json.dumps(cameras, indent=2)

    @mcp.resource("parapilot://pipelines/cfd")
    def cfd_pipelines_resource() -> str:
        """CFD post-processing pipeline examples."""
        examples = {
            "pressure_distribution": {
                "description": "Visualize pressure field on a surface",
                "pipeline": {
                    "source": {"file": "/data/case.foam", "timestep": "latest"},
                    "pipeline": [],
                    "output": {
                        "type": "image",
                        "render": {"field": "p", "colormap": "Cool to Warm"},
                    },
                },
            },
            "velocity_slice": {
                "description": "Velocity magnitude on a cut plane",
                "pipeline": {
                    "source": {"file": "/data/case.foam", "timestep": "latest"},
                    "pipeline": [
                        {"filter": "Slice", "params": {"origin": [0, 0, 0], "normal": [0, 0, 1]}},
                        {
                            "filter": "Calculator",
                            "params": {"expression": "mag(U)", "result_name": "Umag"},
                        },
                    ],
                    "output": {
                        "type": "image",
                        "render": {"field": "Umag", "colormap": "Viridis"},
                    },
                },
            },
            "wall_force_integration": {
                "description": "Compute pressure force on a wall boundary",
                "pipeline": {
                    "source": {"file": "/data/case.foam", "timestep": "latest"},
                    "pipeline": [
                        {"filter": "ExtractBlock", "params": {"selector": "wall"}},
                        {"filter": "GenerateSurfaceNormals"},
                        {
                            "filter": "Calculator",
                            "params": {
                                "expression": "p*Normals",
                                "result_name": "PressureForce",
                            },
                        },
                        {"filter": "IntegrateVariables"},
                    ],
                    "output": {
                        "type": "data",
                        "data": {"fields": ["PressureForce", "Area"]},
                    },
                },
            },
            "streamlines": {
                "description": "Flow visualization with streamlines",
                "pipeline": {
                    "source": {"file": "/data/case.foam", "timestep": "latest"},
                    "pipeline": [
                        {
                            "filter": "StreamTracer",
                            "params": {
                                "seed_point1": [0, -0.1, 0],
                                "seed_point2": [0, 0.1, 0],
                                "seed_resolution": 30,
                                "max_length": 2.0,
                            },
                        },
                    ],
                    "output": {
                        "type": "image",
                        "render": {"field": "U", "colormap": "Viridis"},
                    },
                },
            },
        }
        return json.dumps(examples, indent=2)

    @mcp.resource("parapilot://pipelines/split-animate")
    def split_animate_pipelines_resource() -> str:
        """Split-pane animation examples — multi-view synchronized GIF output."""
        examples = {
            "dual_field_comparison": {
                "description": "Side-by-side comparison of two fields over time",
                "tool": "split_animate",
                "args": {
                    "file_path": "/data/sloshing.pvd",
                    "panes": [
                        {
                            "type": "render", "row": 0, "col": 0,
                            "render_pane": {
                                "render": {
                                    "field": "alpha.water",
                                    "colormap": "Cool to Warm",
                                },
                                "title": "Water Volume Fraction",
                            },
                        },
                        {
                            "type": "render", "row": 0, "col": 1,
                            "render_pane": {
                                "render": {
                                    "field": "p_rgh",
                                    "colormap": "Viridis",
                                },
                                "title": "Pressure",
                            },
                        },
                    ],
                    "layout": {"rows": 1, "cols": 2},
                    "fps": 24, "speed_factor": 5.0,
                },
            },
            "render_plus_graph_2x2": {
                "description": "2x2 grid: two 3D views + two time-series graphs",
                "tool": "split_animate",
                "args": {
                    "file_path": "/data/sloshing.pvd",
                    "panes": [
                        {
                            "type": "render", "row": 0, "col": 0,
                            "render_pane": {
                                "render": {"field": "alpha.water"},
                                "title": "Water",
                            },
                        },
                        {
                            "type": "render", "row": 0, "col": 1,
                            "render_pane": {
                                "render": {
                                    "field": "p_rgh",
                                    "colormap": "Viridis",
                                },
                                "title": "Pressure",
                            },
                        },
                        {
                            "type": "graph", "row": 1, "col": 0,
                            "graph_pane": {
                                "series": [
                                    {"field": "alpha.water", "stat": "mean"},
                                ],
                                "title": "Water Fraction",
                                "y_label": "alpha [-]",
                            },
                        },
                        {
                            "type": "graph", "row": 1, "col": 1,
                            "graph_pane": {
                                "series": [
                                    {"field": "p_rgh", "stat": "max"},
                                    {"field": "p_rgh", "stat": "min"},
                                ],
                                "title": "Pressure Range",
                                "y_label": "p [Pa]",
                            },
                        },
                    ],
                    "layout": {"rows": 2, "cols": 2, "gap": 4},
                    "fps": 24, "speed_factor": 5.0,
                },
            },
            "per_pane_filter": {
                "description": "Each pane with its own filter chain (slice vs full)",
                "tool": "split_animate",
                "args": {
                    "file_path": "/data/case.foam",
                    "panes": [
                        {
                            "type": "render", "row": 0, "col": 0,
                            "render_pane": {
                                "render": {"field": "U", "colormap": "Viridis"},
                                "title": "Full Domain",
                            },
                        },
                        {
                            "type": "render", "row": 0, "col": 1,
                            "render_pane": {
                                "render": {"field": "U", "colormap": "Viridis"},
                                "title": "Mid-Plane Slice",
                                "pipeline": [
                                    {
                                        "filter": "Slice",
                                        "params": {
                                            "origin": [0, 0, 0],
                                            "normal": [0, 0, 1],
                                        },
                                    },
                                ],
                            },
                        },
                    ],
                    "layout": {"rows": 1, "cols": 2},
                    "fps": 24, "speed_factor": 2.0,
                },
            },
        }
        return json.dumps(examples, indent=2)

    @mcp.resource("parapilot://pipelines/fea")
    def fea_pipelines_resource() -> str:
        """FEA post-processing pipeline examples."""
        examples = {
            "deformation": {
                "description": "Visualize deformed shape with stress coloring",
                "pipeline": {
                    "source": {"file": "/data/beam.vtu"},
                    "pipeline": [
                        {
                            "filter": "WarpByVector",
                            "params": {"vector": "displacement", "scale_factor": 10},
                        },
                    ],
                    "output": {
                        "type": "image",
                        "render": {"field": "von_mises_stress", "colormap": "Cool to Warm"},
                    },
                },
            },
            "stress_threshold": {
                "description": "Highlight regions above yield stress",
                "pipeline": {
                    "source": {"file": "/data/part.vtu"},
                    "pipeline": [
                        {
                            "filter": "Threshold",
                            "params": {
                                "field": "von_mises",
                                "lower": 250e6,
                                "upper": 1e9,
                            },
                        },
                    ],
                    "output": {
                        "type": "image",
                        "render": {"field": "von_mises", "colormap": "Cool to Warm"},
                    },
                },
            },
        }
        return json.dumps(examples, indent=2)

    @mcp.resource("parapilot://physics-defaults")
    def physics_defaults_resource() -> str:
        """Physics-aware smart visualization defaults.

        Maps physical quantities to recommended colormap, camera, representation,
        and visualization techniques. Use these defaults when the user doesn't
        specify explicit visualization parameters — just provide the field name
        and the system will choose optimal settings.

        Fields detected: pressure, velocity, temperature, turbulence (k/epsilon/omega),
        stress, displacement, vof (alpha), vorticity, mesh quality, density, wall shear.
        """
        from parapilot.engine.physics import _PHYSICS_PATTERNS

        data: dict[str, dict[str, object]] = {}
        for pattern, props in _PHYSICS_PATTERNS:
            data[props["name"]] = {
                "pattern": pattern,
                "colormap": props["colormap"],
                "diverging": props["diverging"],
                "log_scale": props["log_scale"],
                "camera_2d": props["camera_2d"],
                "camera_3d": props["camera_3d"],
                "representation": props["representation"],
                "warp": props["warp"],
                "streamlines": props["streamlines"],
            }
        data["_usage"] = {  # type: ignore[assignment]
            "description": (
                "When rendering a field, detect the physics type from the field name "
                "and apply the recommended defaults. For unknown fields, use 'cool to warm' "
                "colormap with 'isometric' camera. If data crosses zero, switch to 'coolwarm'."
            ),
        }
        return json.dumps(data, indent=2)


def _format_desc(ext: str) -> str:
    """Short description for file format."""
    descriptions = {
        ".foam": "OpenFOAM case (CFD)",
        ".vtk": "Legacy VTK format",
        ".vtu": "VTK unstructured grid (FEA, general)",
        ".vtp": "VTK polydata (surfaces)",
        ".vts": "VTK structured grid",
        ".vti": "VTK image data (regular grid)",
        ".vtr": "VTK rectilinear grid",
        ".vtm": "VTK multiblock dataset",
        ".pvd": "ParaView data collection (time series)",
        ".stl": "STereoLithography (3D printing, CAD)",
        ".ply": "Polygon file format",
        ".obj": "Wavefront OBJ (3D geometry)",
        ".csv": "Comma-separated values",
        ".cgns": "CFD General Notation System",
        ".exo": "Exodus II (FEA, Sandia)",
        ".e": "Exodus II (alternate extension)",
        ".case": "EnSight Gold format",
        ".cas": "ANSYS Fluent case",
        ".dat": "Tecplot data",
        ".xdmf": "XDMF (HDF5-based, large datasets)",
        ".xmf": "XDMF (alternate extension)",
    }
    return descriptions.get(ext, "")
