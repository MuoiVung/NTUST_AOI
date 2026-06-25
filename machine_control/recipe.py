"""
Recipe/grid generation for the DUO_AOI simulator.

The production system will likely load recipes from a database. For simulator
work, we generate a scan grid from PCB length and width returned by the
SerialTest API. The generated grid is used by the PC/database side for
traceability. The current PLC simulator still uses its internal fixed scan
points until we wire recipe download into the PLC side.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


class RecipeValidationError(ValueError):
    pass


@dataclass(frozen=True)
class RecipeStep:
    step_index: int
    row_idx: int
    col_idx: int
    target_x_mm: float
    target_y_mm: float


@dataclass(frozen=True)
class Recipe:
    name: str
    board_length_mm: float
    board_width_mm: float
    rows: int
    cols: int
    steps: list[RecipeStep]


def validate_board_dimensions(
    length_mm: Optional[float],
    width_mm: Optional[float],
    max_board_length_mm: float = 300.0,
    max_board_width_mm: float = 300.0,
    min_board_mm: float = 1.0,
) -> tuple[float, float]:
    if length_mm is None or width_mm is None:
        raise RecipeValidationError("PCB length and width are required")
    if length_mm < min_board_mm or width_mm < min_board_mm:
        raise RecipeValidationError("PCB dimensions must be positive")
    if length_mm > max_board_length_mm or width_mm > max_board_width_mm:
        raise RecipeValidationError(
            f"PCB dimensions {length_mm} x {width_mm} mm exceed machine limit "
            f"{max_board_length_mm} x {max_board_width_mm} mm"
        )
    return float(length_mm), float(width_mm)


def generate_grid_recipe(
    board_length_mm: float,
    board_width_mm: float,
    fov_step_mm: float = 40.0,
    margin_mm: float = 10.0,
    name: str = "generated-grid",
) -> Recipe:
    if fov_step_mm <= 0:
        raise RecipeValidationError("fov_step_mm must be positive")
    length_mm, width_mm = validate_board_dimensions(board_length_mm, board_width_mm)
    cols = max(1, math.ceil(length_mm / fov_step_mm))
    rows = max(1, math.ceil(width_mm / fov_step_mm))
    usable_length = max(0.0, length_mm - 2 * margin_mm)
    usable_width = max(0.0, width_mm - 2 * margin_mm)
    x_step = usable_length / max(1, cols - 1) if cols > 1 else 0.0
    y_step = usable_width / max(1, rows - 1) if rows > 1 else 0.0

    steps: list[RecipeStep] = []
    index = 0
    for row in range(rows):
        for col in range(cols):
            steps.append(
                RecipeStep(
                    step_index=index,
                    row_idx=row,
                    col_idx=col,
                    target_x_mm=margin_mm + col * x_step,
                    target_y_mm=margin_mm + row * y_step,
                )
            )
            index += 1
    return Recipe(
        name=name,
        board_length_mm=length_mm,
        board_width_mm=width_mm,
        rows=rows,
        cols=cols,
        steps=steps,
    )
