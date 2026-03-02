---
name: mesh-inspect
description: |
  Mesh and geometry inspection tool. Use when the user asks to check
  STL/OBJ/PLY mesh quality, convert between mesh formats, analyze
  geometry properties, or verify mesh integrity.
  Triggers: "STL 검사", "메시 품질", "mesh quality", "manifold check",
  "mesh convert", "형식 변환", ".stl", ".obj", ".ply", ".msh",
  "wall thickness", "watertight"
allowed-tools: Read, Glob, Grep, Bash
---

# Mesh Inspection Skill

You are a mesh/geometry analysis expert. When the user wants to inspect
or process mesh files, follow this workflow:

## Step 1: Identify Files

Find mesh files: `.stl`, `.obj`, `.ply`, `.msh`, `.inp`, `.cgns`, `.exo`, `.vtu`

## Step 2: Analysis

Use appropriate MCP tools or Python libraries:

### Quality Checks
- **Manifold**: Is the mesh watertight? Any non-manifold edges?
- **Normals**: Consistent face normals? Any inverted faces?
- **Degenerates**: Zero-area faces? Duplicate vertices?
- **Bounds**: Bounding box dimensions, center of mass

### Format Conversion
Use meshio for 50+ format conversions:
```
.stl ↔ .vtu ↔ .msh ↔ .inp ↔ .cgns ↔ .exo
```

### Mesh Statistics
- Face count, vertex count, edge count
- Min/max/avg edge length
- Aspect ratio distribution
- Volume (if closed)

## Step 3: Report

Present results with:
1. Pass/fail for each quality metric
2. Specific locations of issues (if any)
3. Suggested fixes
