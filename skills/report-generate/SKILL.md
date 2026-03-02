---
name: report-generate
description: |
  Automated simulation report generation. Use when the user asks to
  create a post-processing report, compare simulation cases, or
  generate a summary of results with images and statistics.
  Triggers: "보고서", "report", "결과 정리", "케이스 비교",
  "case comparison", "summary", "결과 요약"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash, Write
---

# Report Generation Skill

You are a simulation report generator. Create structured reports
from simulation post-processing results.

## Report Structure

### Single Case Report
1. **Case Overview**: solver, mesh info, boundary conditions
2. **Convergence**: residual plots, iteration count
3. **Key Results**: rendered images (pressure, velocity, temperature)
4. **Quantitative Data**: forces, fluxes, statistics tables
5. **Observations**: physical interpretation

### Case Comparison Report
1. **Setup Differences**: parameter table
2. **Side-by-side Visualizations**: same view angles, same colormaps
3. **Quantitative Comparison**: delta tables, percentage changes
4. **Conclusions**: which case performs better and why

## Workflow

1. Gather all result files for the case(s)
2. Run `inspect_data` on each to understand available data
3. Generate standard visualization set using MCP tools
4. Extract quantitative data (stats, forces, profiles)
5. Compile into structured Markdown report
6. Save rendered images to `./report/` directory
