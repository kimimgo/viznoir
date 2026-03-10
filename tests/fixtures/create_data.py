"""Generate test data only (no rendering) — fast."""

import json
import os
from pathlib import Path

from paraview.simple import *

output_dir = os.environ.get("VIZNOIR_OUTPUT_DIR", "/output")
Path(output_dir).mkdir(parents=True, exist_ok=True)

# 1. Wavelet source → VTI
wavelet = Wavelet()
wavelet.WholeExtent = [-10, 10, -10, 10, -10, 10]
wavelet.UpdatePipeline()

vti_path = os.path.join(output_dir, "wavelet.vti")
SaveData(vti_path, proxy=wavelet, DataMode="Binary")

# 2. Inspect: get metadata
data = servermanager.Fetch(wavelet)
info = {
    "file": vti_path,
    "type": data.GetClassName(),
    "num_points": data.GetNumberOfPoints(),
    "num_cells": data.GetNumberOfCells(),
    "bounds": list(data.GetBounds()),
    "point_arrays": [],
}

pd = data.GetPointData()
for i in range(pd.GetNumberOfArrays()):
    arr = pd.GetArray(i)
    info["point_arrays"].append(
        {
            "name": arr.GetName(),
            "components": arr.GetNumberOfComponents(),
            "range": list(arr.GetRange()),
        }
    )

print(json.dumps(info, indent=2))
