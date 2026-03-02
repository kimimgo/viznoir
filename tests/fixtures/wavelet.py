"""Generate test data using ParaView's Wavelet source.

Run inside a ParaView Docker container:
    pvpython /work/wavelet.py

Creates:
    /output/wavelet.vti — ImageData with RTData scalar field
"""

import os
from pathlib import Path

from paraview.simple import *

output_dir = os.environ.get("PARAPILOT_OUTPUT_DIR", "/output")
Path(output_dir).mkdir(parents=True, exist_ok=True)

# Create Wavelet source (built-in test data)
wavelet = Wavelet()
wavelet.WholeExtent = [-10, 10, -10, 10, -10, 10]
wavelet.UpdatePipeline()

# Save as VTI
output_path = os.path.join(output_dir, "wavelet.vti")
SaveData(output_path, proxy=wavelet, DataMode="Binary")

print(f"Created test data: {output_path}")

# Also create a simple rendering to verify
render_view = GetActiveViewOrCreate("RenderView")
render_view.ViewSize = [800, 600]
render_view.Background = [0.32, 0.34, 0.43]

display = Show(wavelet, render_view)
ColorBy(display, ("POINTS", "RTData"))
display.RescaleTransferFunctionToDataRange(True)
display.SetScalarBarVisibility(render_view, True)
render_view.ResetCamera()

screenshot_path = os.path.join(output_dir, "wavelet_test.png")
SaveScreenshot(screenshot_path, render_view, ImageResolution=[800, 600])

print(f"Created test screenshot: {screenshot_path}")
