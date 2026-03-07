"""Custom exception hierarchy for viznoir."""


class ViznoirError(Exception):
    """Base exception for all viznoir errors."""


class FileFormatError(ViznoirError):
    """Unsupported or unrecognized file format."""


class FieldNotFoundError(ViznoirError):
    """Requested field not found in dataset."""


class EmptyOutputError(ViznoirError):
    """Filter or operation produced empty output."""


class RenderError(ViznoirError):
    """Rendering operation failed."""
