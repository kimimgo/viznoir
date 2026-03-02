Use the parapilot plugin to post-process simulation results.

Usage:
  /parapilot render <file> <field>    — Render a field visualization
  /parapilot inspect <file>           — Inspect simulation data
  /parapilot mesh <file>              — Check mesh quality
  /parapilot report <case_dir>        — Generate post-processing report

Examples:
  /parapilot render cavity.foam pressure
  /parapilot inspect results/case.vtk
  /parapilot mesh part.stl
  /parapilot report ./openfoam_case/
