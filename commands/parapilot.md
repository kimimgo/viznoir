Use the viznoir plugin to post-process simulation results.

Usage:
  /viznoir render <file> <field>    — Render a field visualization
  /viznoir inspect <file>           — Inspect simulation data
  /viznoir mesh <file>              — Check mesh quality
  /viznoir report <case_dir>        — Generate post-processing report

Examples:
  /viznoir render cavity.foam pressure
  /viznoir inspect results/case.vtk
  /viznoir mesh part.stl
  /viznoir report ./openfoam_case/
