"""Easing functions for animation — inspired by Manim rate_functions.

All functions: f(0) = 0, f(1) = 1, with varying interpolation curves.
Exception: there_and_back returns to 0 at t=1.

Reference: github.com/ManimCommunity/manim  manim/utils/rate_functions.py
"""

from __future__ import annotations

import math
from collections.abc import Callable


def linear(t: float) -> float:
    """Constant speed."""
    return t


def smooth(t: float) -> float:
    """Smooth ease-in-out (smoothstep)."""
    return t * t * (3.0 - 2.0 * t)


def double_smooth(t: float) -> float:
    """Extra-smooth — applies smooth twice: smooth(smooth(t))."""
    return smooth(smooth(t))


def ease_in_sine(t: float) -> float:
    """Sine-based slow start."""
    return 1.0 - math.cos(t * math.pi / 2.0)


def ease_out_sine(t: float) -> float:
    """Sine-based slow end."""
    return math.sin(t * math.pi / 2.0)


def ease_in_out_sine(t: float) -> float:
    """Sine-based slow start and end."""
    return -(math.cos(math.pi * t) - 1.0) / 2.0


def ease_in_quad(t: float) -> float:
    """Quadratic ease-in."""
    return t * t


def ease_out_quad(t: float) -> float:
    """Quadratic ease-out."""
    return t * (2.0 - t)


def ease_in_out_quad(t: float) -> float:
    """Quadratic ease-in-out."""
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0


def ease_in_cubic(t: float) -> float:
    """Cubic ease-in."""
    return t * t * t


def ease_out_cubic(t: float) -> float:
    """Cubic ease-out."""
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    """Cubic ease-in-out."""
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0


def ease_in_expo(t: float) -> float:
    """Exponential ease-in."""
    return 0.0 if t == 0.0 else 2.0 ** (10.0 * t - 10.0)


def ease_out_expo(t: float) -> float:
    """Exponential ease-out."""
    return 1.0 if t == 1.0 else 1.0 - 2.0 ** (-10.0 * t)


def there_and_back(t: float) -> float:
    """Go to 1.0 at t=0.5, return to 0.0 at t=1.0 (ping-pong)."""
    return smooth(2.0 * t) if t < 0.5 else smooth(2.0 * (1.0 - t))


def rush_into(t: float) -> float:
    """Accelerating — slow start, fast end."""
    return 2.0 * smooth(t / 2.0)


def rush_from(t: float) -> float:
    """Decelerating — fast start, slow end."""
    return 2.0 * smooth(t / 2.0 + 0.5) - 1.0


EASING_FUNCTIONS: dict[str, Callable[[float], float]] = {
    "linear": linear,
    "smooth": smooth,
    "double_smooth": double_smooth,
    "ease_in": ease_in_quad,
    "ease_out": ease_out_quad,
    "ease_in_out": ease_in_out_cubic,
    "ease_in_sine": ease_in_sine,
    "ease_out_sine": ease_out_sine,
    "ease_in_out_sine": ease_in_out_sine,
    "ease_in_quad": ease_in_quad,
    "ease_out_quad": ease_out_quad,
    "ease_in_out_quad": ease_in_out_quad,
    "ease_in_cubic": ease_in_cubic,
    "ease_out_cubic": ease_out_cubic,
    "ease_in_out_cubic": ease_in_out_cubic,
    "ease_in_expo": ease_in_expo,
    "ease_out_expo": ease_out_expo,
    "there_and_back": there_and_back,
    "rush_into": rush_into,
    "rush_from": rush_from,
}
