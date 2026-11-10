"""Duration view's knot: dots of varying size flowing along a trefoil knot that tumbles in 3D
while the duration runs, slowing to a stop and swelling into one solid tube when it pauses.
While paused it can be dragged round like a trackball and flicked to coast, a fidget toy.

Pure maths, no Qt: advance the state by elapsed time, then read the dots to draw. Coordinates
are fractions of the drawing's half-size, origin at the centre. The knot (tube included) fits
inside the unit sphere, so it stays inside [-1, 1] on screen at every rotation.

The trefoil is resampled at equal 3D arc lengths once at import, so dots are spaced evenly
and the solid tube has no gaps where the curve's parameter speeds up. Rotation and an
orthographic projection only ever shorten on-screen gaps, so the tube stays gapless at any
angle.
"""

import bisect
import math
import random
from typing import NamedTuple

DOT_COUNT = 300  # dense enough that neighbouring dots in the solid tube differ by a hair of shade
ARC_LENGTH_TABLE_SIZE = 2048
CURVE_SAMPLES_FOR_ARC_LENGTH = 8192
SOLID_TUBE_RADIUS = 0.085
SMALLEST_RUNNING_DOT_RADIUS = 0.008
LARGEST_RUNNING_DOT_RADIUS = 0.032
RUNNING_WOBBLE_AMPLITUDE = 0.05  # how far a running dot drifts either side of the knot
FLOW_LAPS_PER_SECOND = 0.012  # one trip round the knot every ~80 s
WOBBLE_RADIANS_PER_SECOND = 1.6
AUTO_SPIN_RADIANS_PER_SECOND = 0.35  # one turn every ~18 s
# The spin axis leans this far off the line of sight, so the knot tips up to twice this
# (80°) away from face-on and back each turn, showing its depth without lying flat for long.
AUTO_SPIN_AXIS_TILT_FROM_VIEW_RADIANS = math.radians(40)
AUTO_SPIN_AXIS_TURN_IN_SCREEN_RADIANS = math.radians(60)  # which way it leans: down-right
# Dragging across the drawing's half-size turns the knot this far (about 140°).
DRAG_RADIANS_PER_HALF_SIZE = 2.5
# A flick hands its spin to the knot, which coasts and slows like a fidget spinner.
COAST_SPEED_HALF_LIFE_SECONDS = 0.9
COAST_STOP_RADIANS_PER_SECOND = 0.05  # slower than this reads as stopped, so stop redrawing
MAXIMUM_FLICK_RADIANS_PER_SECOND = 14.0
# Letting go after holding still this long is a drop, not a flick: no coasting.
HELD_STILL_BEFORE_RELEASE_SECONDS = 0.08
SHORTEST_DRAG_STEP_SECONDS = 1 / 240  # two pointer events close together don't spike the speed
DRAG_SPEED_SMOOTHING = 0.5  # weight of the newest drag step in the flick speed
SOLIDIFY_SECONDS = 0.7  # running → solid, and back
DOT_LAYOUT_RANDOM_SEED = 7

Point3D = tuple[float, float, float]
Orientation = tuple[Point3D, Point3D, Point3D]  # rows of a 3x3 rotation matrix
FACE_ON_ORIENTATION: Orientation = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


class KnotDot(NamedTuple):
    x: float
    y: float
    radius: float
    depth: float  # -1 farthest from the viewer, +1 nearest (stretched to fill the range each frame)


class _KnotSample(NamedTuple):
    position: Point3D
    wobble_direction: Point3D  # unit, across the curve within the knot's face-on plane


def _trefoil_point(curve_parameter: float) -> Point3D:
    return (
        math.sin(curve_parameter) + 2 * math.sin(2 * curve_parameter),
        -(math.cos(curve_parameter) - 2 * math.cos(2 * curve_parameter)),  # lobe at the top
        -math.sin(3 * curve_parameter),
    )


def _build_equal_arc_length_samples() -> list[_KnotSample]:
    dense_points = [
        _trefoil_point(2 * math.pi * sample_index / CURVE_SAMPLES_FOR_ARC_LENGTH)
        for sample_index in range(CURVE_SAMPLES_FOR_ARC_LENGTH + 1)
    ]
    cumulative_lengths = [0.0]
    for previous_point, point in zip(dense_points, dense_points[1:], strict=False):
        cumulative_lengths.append(cumulative_lengths[-1] + math.dist(previous_point, point))
    total_length = cumulative_lengths[-1]

    equal_arc_points = []
    for table_index in range(ARC_LENGTH_TABLE_SIZE):
        target_length = total_length * table_index / ARC_LENGTH_TABLE_SIZE
        dense_index = min(
            bisect.bisect_left(cumulative_lengths, target_length), CURVE_SAMPLES_FOR_ARC_LENGTH
        )
        equal_arc_points.append(dense_points[dense_index])

    centre = tuple(
        (
            min(point[axis] for point in equal_arc_points)
            + max(point[axis] for point in equal_arc_points)
        )
        / 2
        for axis in range(3)
    )
    centred_points = [(x - centre[0], y - centre[1], z - centre[2]) for x, y, z in equal_arc_points]
    bounding_radius = max(math.hypot(*point) for point in centred_points)
    # Leave room for the tube, or a running dot's wobble, whichever reaches further.
    margin = max(SOLID_TUBE_RADIUS, RUNNING_WOBBLE_AMPLITUDE + LARGEST_RUNNING_DOT_RADIUS)
    scale = (1 - margin) / bounding_radius
    scaled_points = [(x * scale, y * scale, z * scale) for x, y, z in centred_points]

    samples = []
    for table_index, position in enumerate(scaled_points):
        previous_x, previous_y, _ = scaled_points[table_index - 1]
        next_x, next_y, _ = scaled_points[(table_index + 1) % ARC_LENGTH_TABLE_SIZE]
        tangent_x, tangent_y = next_x - previous_x, next_y - previous_y
        tangent_length = math.hypot(tangent_x, tangent_y)
        wobble_direction = (-tangent_y / tangent_length, tangent_x / tangent_length, 0.0)
        samples.append(_KnotSample(position, wobble_direction))
    return samples


def rotation_about_axis(axis: Point3D, rotation_radians: float) -> Orientation:
    """Turn `rotation_radians` about `axis` (any length), right-handed (Rodrigues' formula).

    Screen axes: x right, y down, z towards the viewer.
    """
    axis_length = math.hypot(*axis)
    if axis_length == 0:
        raise ValueError("A rotation axis needs a direction, got the zero vector")
    axis_x, axis_y, axis_z = (component / axis_length for component in axis)
    cosine, sine = math.cos(rotation_radians), math.sin(rotation_radians)
    one_minus_cosine = 1 - cosine
    return (
        (
            cosine + axis_x * axis_x * one_minus_cosine,
            axis_x * axis_y * one_minus_cosine - axis_z * sine,
            axis_x * axis_z * one_minus_cosine + axis_y * sine,
        ),
        (
            axis_y * axis_x * one_minus_cosine + axis_z * sine,
            cosine + axis_y * axis_y * one_minus_cosine,
            axis_y * axis_z * one_minus_cosine - axis_x * sine,
        ),
        (
            axis_z * axis_x * one_minus_cosine - axis_y * sine,
            axis_z * axis_y * one_minus_cosine + axis_x * sine,
            cosine + axis_z * axis_z * one_minus_cosine,
        ),
    )


def _then_rotate(orientation: Orientation, rotation: Orientation) -> Orientation:
    """`orientation` followed by `rotation`, both in screen axes (rotation · orientation)."""
    return tuple(
        tuple(
            sum(rotation[row][step] * orientation[step][column] for step in range(3))
            for column in range(3)
        )
        for row in range(3)
    )


_AUTO_SPIN_AXIS: Point3D = (
    math.sin(AUTO_SPIN_AXIS_TILT_FROM_VIEW_RADIANS)
    * math.cos(AUTO_SPIN_AXIS_TURN_IN_SCREEN_RADIANS),
    math.sin(AUTO_SPIN_AXIS_TILT_FROM_VIEW_RADIANS)
    * math.sin(AUTO_SPIN_AXIS_TURN_IN_SCREEN_RADIANS),
    math.cos(AUTO_SPIN_AXIS_TILT_FROM_VIEW_RADIANS),
)


_EQUAL_ARC_LENGTH_SAMPLES = _build_equal_arc_length_samples()
_dot_layout_random = random.Random(DOT_LAYOUT_RANDOM_SEED)
_RUNNING_DOT_RADII = [
    _dot_layout_random.uniform(SMALLEST_RUNNING_DOT_RADIUS, LARGEST_RUNNING_DOT_RADIUS)
    for _ in range(DOT_COUNT)
]
_WOBBLE_PHASE_OFFSETS_RADIANS = [
    _dot_layout_random.uniform(0, 2 * math.pi) for _ in range(DOT_COUNT)
]


def knot_dots(
    flow_laps: float, wobble_radians: float, orientation: Orientation, solidity: float
) -> list[KnotDot]:
    """The dots at a moment: `flow_laps` is how far they have travelled round the knot,
    `orientation` how the knot is turned, and `solidity` 0 is loose running dots and 1 the
    solid tube (wobble and size variety gone)."""
    if not 0 <= solidity <= 1:
        raise ValueError(f"Knot solidity must be between 0 and 1, got {solidity}")
    eased_solidity = solidity * solidity * (3 - 2 * solidity)  # smoothstep
    looseness = 1 - eased_solidity

    rotated_points: list[Point3D] = []
    for dot_index in range(DOT_COUNT):
        lap_fraction = (dot_index / DOT_COUNT + flow_laps) % 1.0
        table_position = lap_fraction * ARC_LENGTH_TABLE_SIZE
        lower_index = int(table_position) % ARC_LENGTH_TABLE_SIZE
        upper_index = (lower_index + 1) % ARC_LENGTH_TABLE_SIZE
        blend = table_position - int(table_position)
        lower_sample = _EQUAL_ARC_LENGTH_SAMPLES[lower_index]
        upper_sample = _EQUAL_ARC_LENGTH_SAMPLES[upper_index]
        wobble_offset = (
            RUNNING_WOBBLE_AMPLITUDE
            * looseness
            * math.sin(wobble_radians + _WOBBLE_PHASE_OFFSETS_RADIANS[dot_index])
        )
        point = tuple(
            _lerp(lower_sample.position[axis], upper_sample.position[axis], blend)
            + wobble_offset * lower_sample.wobble_direction[axis]
            for axis in range(3)
        )
        rotated_points.append(
            tuple(sum(row[axis] * point[axis] for axis in range(3)) for row in orientation)
        )

    nearest_z = max(point[2] for point in rotated_points)
    farthest_z = min(point[2] for point in rotated_points)
    return [
        KnotDot(
            x=x,
            y=y,
            radius=_lerp(_RUNNING_DOT_RADII[dot_index], SOLID_TUBE_RADIUS, eased_solidity),
            depth=2 * (z - farthest_z) / (nearest_z - farthest_z) - 1,
        )
        for dot_index, (x, y, z) in enumerate(rotated_points)
    ]


class KnotAnimationState:
    """Where the dots are, how the knot is turned and how solid it is. Starts solid and face-on,
    since a fresh duration is stopped.

    While running, solidity falls to 0 and the dots flow and wobble while the knot spins about
    a tilted axis; while paused it rises to 1 and all of that slows to a stop with it, so the
    dots freeze, at whatever angle the knot reached, exactly as they join up.

    While paused the knot is a fidget toy: `grab` takes hold (stopping any coast), `turn_by_drag`
    turns it like a trackball (the front follows the pointer) and `release_drag` lets a flick
    coast and slow down. Starting the timer
    cancels any drag or coast and hands over to the auto-spin from wherever the knot was left.
    The owner stops calling `turn_by_drag` while the timer runs.
    """

    def __init__(self) -> None:
        self.flow_laps = 0.0
        self.wobble_radians = 0.0
        self.orientation = FACE_ON_ORIENTATION
        self.solidity = 1.0
        # Angular velocity as a vector: its direction is the spin axis, its length the speed.
        self._coast_angular_velocity: Point3D = (0.0, 0.0, 0.0)
        self._is_being_dragged = False

    @property
    def is_settled(self) -> bool:
        """Solid and still: nothing changes until the timer runs or the knot is dragged."""
        return self.solidity == 1.0 and self._coast_angular_velocity == (0.0, 0.0, 0.0)

    def advance(self, elapsed_seconds: float, is_timer_running: bool) -> None:
        if elapsed_seconds < 0:
            raise ValueError(f"Animation time can't go backwards, got {elapsed_seconds} s")
        solidity_step = elapsed_seconds / SOLIDIFY_SECONDS
        if is_timer_running:
            self.solidity = max(0.0, self.solidity - solidity_step)
            self._is_being_dragged = False
            self._coast_angular_velocity = (0.0, 0.0, 0.0)
        else:
            self.solidity = min(1.0, self.solidity + solidity_step)
        motion_speed = 1 - self.solidity
        self.flow_laps = (
            self.flow_laps + FLOW_LAPS_PER_SECOND * motion_speed * elapsed_seconds
        ) % 1.0
        self.wobble_radians = (
            self.wobble_radians + WOBBLE_RADIANS_PER_SECOND * motion_speed * elapsed_seconds
        ) % (2 * math.pi)
        auto_spin_radians = AUTO_SPIN_RADIANS_PER_SECOND * motion_speed * elapsed_seconds
        if auto_spin_radians:
            self._rotate(rotation_about_axis(_AUTO_SPIN_AXIS, auto_spin_radians))
        if not self._is_being_dragged:
            self._coast(elapsed_seconds)

    def grab(self) -> None:
        """Take hold, as a pointer press does: a coasting knot stops dead, like a caught spinner."""
        self._is_being_dragged = True
        self._coast_angular_velocity = (0.0, 0.0, 0.0)

    def turn_by_drag(
        self, drag_x: float, drag_y: float, seconds_since_previous_drag_step: float
    ) -> None:
        """While held, the pointer moved by (drag_x, drag_y) in fractions of the drawing's
        half-size."""
        if not self._is_being_dragged:
            raise ValueError("The knot must be grabbed before it can be dragged")
        if seconds_since_previous_drag_step < 0:
            raise ValueError(
                f"Drag steps can't go back in time, got {seconds_since_previous_drag_step} s"
            )
        drag_length = math.hypot(drag_x, drag_y)
        if drag_length == 0:
            return
        turn_radians = drag_length * DRAG_RADIANS_PER_HALF_SIZE
        # Perpendicular to the drag in the screen plane, so the knot's front moves with it.
        turn_axis = (-drag_y, drag_x, 0.0)
        self._rotate(rotation_about_axis(turn_axis, turn_radians))

        step_seconds = max(seconds_since_previous_drag_step, SHORTEST_DRAG_STEP_SECONDS)
        step_speed = turn_radians / step_seconds
        step_angular_velocity = tuple(
            component / drag_length * step_speed for component in turn_axis
        )
        self._coast_angular_velocity = tuple(
            (1 - DRAG_SPEED_SMOOTHING) * previous + DRAG_SPEED_SMOOTHING * newest
            for previous, newest in zip(
                self._coast_angular_velocity, step_angular_velocity, strict=True
            )
        )

    def release_drag(self, seconds_since_last_drag_step: float) -> None:
        """Let go: keep spinning if the pointer was still moving (a flick), else stop."""
        self._is_being_dragged = False
        coast_speed = math.hypot(*self._coast_angular_velocity)
        if seconds_since_last_drag_step > HELD_STILL_BEFORE_RELEASE_SECONDS or coast_speed == 0:
            self._coast_angular_velocity = (0.0, 0.0, 0.0)
        elif coast_speed > MAXIMUM_FLICK_RADIANS_PER_SECOND:
            self._coast_angular_velocity = tuple(
                component * MAXIMUM_FLICK_RADIANS_PER_SECOND / coast_speed
                for component in self._coast_angular_velocity
            )

    def dots(self) -> list[KnotDot]:
        return knot_dots(self.flow_laps, self.wobble_radians, self.orientation, self.solidity)

    def _rotate(self, rotation: Orientation) -> None:
        self.orientation = _then_rotate(self.orientation, rotation)

    def _coast(self, elapsed_seconds: float) -> None:
        coast_speed = math.hypot(*self._coast_angular_velocity)
        if coast_speed == 0:
            return
        self._rotate(
            rotation_about_axis(self._coast_angular_velocity, coast_speed * elapsed_seconds)
        )
        speed_kept = 0.5 ** (elapsed_seconds / COAST_SPEED_HALF_LIFE_SECONDS)
        if coast_speed * speed_kept < COAST_STOP_RADIANS_PER_SECOND:
            self._coast_angular_velocity = (0.0, 0.0, 0.0)
        else:
            self._coast_angular_velocity = tuple(
                component * speed_kept for component in self._coast_angular_velocity
            )


def _lerp(start: float, end: float, blend: float) -> float:
    return start + (end - start) * blend
