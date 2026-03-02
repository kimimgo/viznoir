Use the mechkit plugin to post-process simulation results.

Usage:
  /mechkit render <file> <field>    — Render a field visualization
  /mechkit inspect <file>           — Inspect simulation data
  /mechkit mesh <file>              — Check mesh quality
  /mechkit report <case_dir>        — Generate post-processing report

Examples:
  /mechkit render cavity.foam pressure
  /mechkit inspect results/case.vtk
  /mechkit mesh part.stl
  /mechkit report ./openfoam_case/
