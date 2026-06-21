# Domain Gallery

viznoir works across science and engineering domains. Each section shows the
typical fields, the tools that fit, and a starting workflow. See
[tools/reference.md](./tools/reference.md) for full tool signatures.

## CFD — Computational Fluid Dynamics

- **Formats**: OpenFOAM (`.foam`), CGNS, ANSYS Fluent (`.cas`/`.dat`), VTK.
- **Fields**: velocity `U` (vector), pressure `p` (signed), temperature `T`.
- **Workflow**: `inspect_data` → `slice`/`streamlines` for the flow →
  `contour` for iso-surfaces → `inspect_physics` for vortices/critical points →
  `validate_render` to confirm a diverging colormap on signed pressure.
- **Tip**: pressure crosses zero — use a diverging, zero-centered colormap
  (`coolwarm`); velocity magnitude is one-sided — use a sequential map.

## FEA — Structural / Finite Element

- **Formats**: Exodus, VTU/VTK.
- **Fields**: displacement (vector), von Mises stress, strain.
- **Workflow**: `inspect_data` → `warp_by_vector` to exaggerate displacement →
  `render`/`cinematic_render` coloured by stress → `extract_stats` for max stress.
- **Tip**: stress is non-negative — sequential colormap; warp scale is for
  visualization only.

## Medical — Imaging / Volumes

- **Formats**: MRC/MAP (cryoEM electron density), VTI, DICOM-derived volumes.
- **Fields**: scalar intensity / density.
- **Workflow**: `inspect_data` → `volume` render with a transfer-function preset
  → `pv_isosurface` for a surface at a chosen density → `preview_3d` to export glTF.
- **Tip**: pick isovalues inside the data range — `validate_render` flags an
  empty isosurface and suggests the range.

## Geo — Earth / Terrain

- **Formats**: VTK structured/unstructured grids, terrain meshes.
- **Fields**: elevation, scalar overlays.
- **Workflow**: `render` with the `terrain` colormap → `slice` for cross-sections
  → `plot_over_line` for profiles.

## Molecular

- **Formats**: chemistry-capable VTK readers, point clouds.
- **Fields**: per-atom scalars, density.
- **Workflow**: `glyph` for atoms/vectors → `cinematic_render` (PBR + SSAO) for
  publication figures.

---

For ready-to-run examples across 14 countries and many domains, see
[showcase-gallery.md](./showcase-gallery.md).
