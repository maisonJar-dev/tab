"""Splash intro geometry: a wireframe cube falls, bounces, spins, then its 12 edges fly apart
and land as the 12 strokes of "tab".

Pure maths, no Qt: given a time, return the line segments to draw. Coordinates are pixels
with the origin at the centre of the viewport and y pointing down.

Timeline (seconds):
    0.00 - 0.70  fall      drops from above the window under gravity
    0.70 - 1.34  bounce    two diminishing bounces, squashing a little on each contact
    1.34 - 3.14  spin      lifts to the centre and spins up
    3.14 - 4.84  assemble  edges drift apart turning, then glide left-to-right into the word
"""

import math
import random
from typing import NamedTuple

Point = tuple[float, float]
LineSegment = tuple[Point, Point]
Point3D = tuple[float, float, float]

# ---- timeline -------------------------------------------------------------------------------
FALL_DURATION_SECONDS = 0.70
FIRST_BOUNCE_DURATION_SECONDS = 0.42
SECOND_BOUNCE_DURATION_SECONDS = 0.22
SPIN_DURATION_SECONDS = 1.80
ASSEMBLE_DURATION_SECONDS = 1.70

FIRST_LANDING_SECONDS = FALL_DURATION_SECONDS
SECOND_LANDING_SECONDS = FIRST_LANDING_SECONDS + FIRST_BOUNCE_DURATION_SECONDS
FINAL_LANDING_SECONDS = SECOND_LANDING_SECONDS + SECOND_BOUNCE_DURATION_SECONDS
ASSEMBLE_START_SECONDS = FINAL_LANDING_SECONDS + SPIN_DURATION_SECONDS
TOTAL_DURATION_SECONDS = ASSEMBLE_START_SECONDS + ASSEMBLE_DURATION_SECONDS

# ---- proportions (fractions of the overall animation scale) ---------------------------------
CUBE_EDGE_LENGTH_FRACTION = 0.40
STROKE_WIDTH_FRACTION = 0.032  # cube edges and letter strokes share one width
WORD_X_HEIGHT_FRACTION = 0.48
MINIMUM_SCALE_PIXELS = 40.0

# ---- motion ---------------------------------------------------------------------------------
CUBE_TILT_TOWARD_VIEWER_RADIANS = 0.55
CUBE_IDLE_SPIN_RADIANS_PER_SECOND = 0.9
CUBE_INITIAL_SPIN_RADIANS = 0.6
CUBE_PEAK_SPIN_RADIANS_PER_SECOND = 11.0
CAMERA_DISTANCE_IN_CUBE_EDGES = 7
BOUNCE_HEIGHTS_AS_FRACTION_OF_DROP = (0.16, 0.045)
SQUASH_AMOUNT_AT_EACH_LANDING = (0.18, 0.08, 0.035)
SQUASH_DURATION_SECONDS = 0.045
SQUASH_HORIZONTAL_SPREAD = 0.7
LIFT_TO_CENTRE_FRACTION_OF_SPIN = 0.4
EDGE_DRIFT_OUT_SECONDS = 0.6
EDGE_GLIDE_HOME_DELAY_SECONDS = 0.3
EDGE_GLIDE_HOME_SECONDS = 1.0
MAXIMUM_LEFT_TO_RIGHT_STAGGER_SECONDS = 0.35
FLIGHT_PLAN_RANDOM_SEED = 5

# ---- shapes ---------------------------------------------------------------------------------
CUBE_VERTICES: list[Point3D] = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
CUBE_EDGES: list[tuple[int, int]] = [
    (first_index, second_index)
    for first_index in range(8)
    for second_index in range(first_index + 1, 8)
    if sum(
        a != b for a, b in zip(CUBE_VERTICES[first_index], CUBE_VERTICES[second_index], strict=True)
    )
    == 1
]

# "tab" as straight strokes in x-height units (y up is negative), one per cube edge.
TAB_WORD_STROKES: list[LineSegment] = [
    # t
    ((0.30, -1.55), (0.30, 0.00)),
    ((0.00, -1.00), (0.65, -1.00)),
    ((0.30, 0.00), (0.62, 0.00)),
    # a
    ((1.00, -1.00), (1.70, -1.00)),
    ((1.70, -1.00), (1.70, 0.00)),
    ((1.70, 0.00), (1.00, 0.00)),
    ((1.00, 0.00), (1.00, -0.50)),
    ((1.00, -0.50), (1.70, -0.50)),
    # b
    ((2.10, -1.55), (2.10, 0.00)),
    ((2.10, -1.00), (2.80, -1.00)),
    ((2.80, -1.00), (2.80, 0.00)),
    ((2.80, 0.00), (2.10, 0.00)),
]

if len(TAB_WORD_STROKES) != len(CUBE_EDGES):
    raise ValueError(
        f"The word needs one stroke per cube edge: {len(TAB_WORD_STROKES)} strokes, "
        f"{len(CUBE_EDGES)} edges"
    )


# ---- easing and geometry helpers ------------------------------------------------------------
def clamp(value: float, lower_bound: float = 0.0, upper_bound: float = 1.0) -> float:
    return max(lower_bound, min(value, upper_bound))


def smootherstep(progress: float) -> float:
    """Ken Perlin's 6t^5 - 15t^4 + 10t^3: zero velocity and acceleration at both ends."""
    progress = clamp(progress)
    return progress**3 * (progress * (6 * progress - 15) + 10)


def ease_out_cubic(progress: float) -> float:
    return 1 - (1 - clamp(progress)) ** 3


def lerp(start: float, end: float, progress: float) -> float:
    return start + (end - start) * progress


def rotate_spin_then_tilt(vertex: Point3D, spin_radians: float, tilt_radians: float) -> Point3D:
    """Spin about the vertical axis, then lean the top toward the viewer."""
    x, y, z = vertex
    x, z = (
        x * math.cos(spin_radians) + z * math.sin(spin_radians),
        -x * math.sin(spin_radians) + z * math.cos(spin_radians),
    )
    y, z = (
        y * math.cos(tilt_radians) - z * math.sin(tilt_radians),
        y * math.sin(tilt_radians) + z * math.cos(tilt_radians),
    )
    return x, y, z


class Stick(NamedTuple):
    """A line segment described by its middle, angle and length, which interpolates cleanly."""

    centre_x: float
    centre_y: float
    angle_radians: float
    length: float

    @classmethod
    def from_segment(cls, segment: LineSegment) -> "Stick":
        (start_x, start_y), (end_x, end_y) = segment
        return cls(
            (start_x + end_x) / 2,
            (start_y + end_y) / 2,
            math.atan2(end_y - start_y, end_x - start_x),
            math.hypot(end_x - start_x, end_y - start_y),
        )

    def to_segment(self) -> LineSegment:
        half_dx = math.cos(self.angle_radians) * self.length / 2
        half_dy = math.sin(self.angle_radians) * self.length / 2
        return (
            (self.centre_x - half_dx, self.centre_y - half_dy),
            (self.centre_x + half_dx, self.centre_y + half_dy),
        )


class EdgeFlight(NamedTuple):
    """How one cube edge travels to its stroke in the word."""

    edge_at_burst: Stick
    stroke_in_word: Stick
    drift_out_x: float
    drift_out_y: float
    drift_turn_radians: float
    glide_home_delay_seconds: float


def animation_scale_for_viewport(viewport_width: float, viewport_height: float) -> float:
    return max(MINIMUM_SCALE_PIXELS, min(viewport_width * 0.26, viewport_height * 0.40))


# ---- the animation --------------------------------------------------------------------------
class CubeToWordAnimation:
    """Answers "which line segments are on screen at time t?" for one viewport size."""

    def __init__(
        self,
        scale_pixels: float,
        viewport_height_pixels: float,
        random_seed: int = FLIGHT_PLAN_RANDOM_SEED,
    ) -> None:
        self._scale_pixels = scale_pixels
        self._viewport_height_pixels = viewport_height_pixels
        self.word_segments = self._word_segments_centred_on_origin()
        self._edge_flights = self._plan_edge_flights(random_seed)

    @property
    def stroke_width_pixels(self) -> float:
        return self._scale_pixels * STROKE_WIDTH_FRACTION

    @property
    def ground_y_pixels(self) -> float:
        """Where the cube lands: a little below the word's baseline."""
        x_height_pixels = self._scale_pixels * WORD_X_HEIGHT_FRACTION
        return x_height_pixels * 0.8 + self._scale_pixels * 0.35

    def line_segments_at(self, elapsed_seconds: float) -> list[LineSegment]:
        if elapsed_seconds < ASSEMBLE_START_SECONDS:
            cube_corners = self._cube_corners_on_screen(elapsed_seconds)
            return [(cube_corners[first], cube_corners[second]) for first, second in CUBE_EDGES]
        seconds_since_burst = min(elapsed_seconds, TOTAL_DURATION_SECONDS) - ASSEMBLE_START_SECONDS
        return [
            _edge_in_flight(edge_flight, seconds_since_burst).to_segment()
            for edge_flight in self._edge_flights
        ]

    # -- word --
    def _word_segments_centred_on_origin(self) -> list[LineSegment]:
        x_height_pixels = self._scale_pixels * WORD_X_HEIGHT_FRACTION
        stroke_xs = [x for stroke in TAB_WORD_STROKES for x, _ in stroke]
        stroke_ys = [y for stroke in TAB_WORD_STROKES for _, y in stroke]
        word_centre_x = (min(stroke_xs) + max(stroke_xs)) / 2
        word_centre_y = (min(stroke_ys) + max(stroke_ys)) / 2
        return [
            (
                (
                    (start_x - word_centre_x) * x_height_pixels,
                    (start_y - word_centre_y) * x_height_pixels,
                ),
                (
                    (end_x - word_centre_x) * x_height_pixels,
                    (end_y - word_centre_y) * x_height_pixels,
                ),
            )
            for (start_x, start_y), (end_x, end_y) in TAB_WORD_STROKES
        ]

    # -- cube --
    def _cube_corners_on_screen(self, elapsed_seconds: float) -> list[Point]:
        cube_edge_pixels = self._scale_pixels * CUBE_EDGE_LENGTH_FRACTION
        half_edge_pixels = cube_edge_pixels / 2
        camera_distance_pixels = cube_edge_pixels * CAMERA_DISTANCE_IN_CUBE_EDGES

        projected_corners = []
        for vertex in CUBE_VERTICES:
            x, y, z = rotate_spin_then_tilt(
                vertex, _cube_spin_radians(elapsed_seconds), CUBE_TILT_TOWARD_VIEWER_RADIANS
            )
            perspective = camera_distance_pixels / (camera_distance_pixels - z * half_edge_pixels)
            projected_corners.append(
                (x * half_edge_pixels * perspective, y * half_edge_pixels * perspective)
            )

        lowest_corner_y = max(y for _, y in projected_corners)
        lift_to_centre = smootherstep(
            (elapsed_seconds - FINAL_LANDING_SECONDS)
            / (SPIN_DURATION_SECONDS * LIFT_TO_CENTRE_FRACTION_OF_SPIN)
        )
        resting_offset_y = (
            self.ground_y_pixels - lowest_corner_y - self._height_above_ground(elapsed_seconds)
        )
        offset_y = lerp(resting_offset_y, 0.0, lift_to_centre)

        vertical_squash = _vertical_squash(elapsed_seconds)
        horizontal_spread = 1 + (1 - vertical_squash) * SQUASH_HORIZONTAL_SPREAD
        return [
            (
                x * horizontal_spread,
                (y - lowest_corner_y) * vertical_squash + lowest_corner_y + offset_y,
            )
            for x, y in projected_corners
        ]

    def _height_above_ground(self, elapsed_seconds: float) -> float:
        drop_height_pixels = (
            self.ground_y_pixels
            + self._viewport_height_pixels / 2
            + self._scale_pixels * CUBE_EDGE_LENGTH_FRACTION * 2
        )
        if elapsed_seconds < FIRST_LANDING_SECONDS:
            fall_progress = elapsed_seconds / FALL_DURATION_SECONDS
            return drop_height_pixels * (1 - fall_progress**2)
        bounces = (
            (FIRST_LANDING_SECONDS, FIRST_BOUNCE_DURATION_SECONDS),
            (SECOND_LANDING_SECONDS, SECOND_BOUNCE_DURATION_SECONDS),
        )
        for (bounce_start_seconds, bounce_duration_seconds), bounce_height_fraction in zip(
            bounces, BOUNCE_HEIGHTS_AS_FRACTION_OF_DROP, strict=True
        ):
            if elapsed_seconds < bounce_start_seconds + bounce_duration_seconds:
                bounce_progress = (elapsed_seconds - bounce_start_seconds) / bounce_duration_seconds
                parabola = 4 * bounce_progress * (1 - bounce_progress)
                return drop_height_pixels * bounce_height_fraction * parabola
        return 0.0

    # -- flight plan --
    def _plan_edge_flights(self, random_seed: int) -> list[EdgeFlight]:
        """Pair edges with strokes left-to-right, so no edge has to cross the whole word."""
        burst_corners = self._cube_corners_on_screen(ASSEMBLE_START_SECONDS)
        edges_at_burst = [
            Stick.from_segment((burst_corners[first], burst_corners[second]))
            for first, second in CUBE_EDGES
        ]
        strokes_in_word = [Stick.from_segment(segment) for segment in self.word_segments]
        edges_left_to_right = sorted(edges_at_burst, key=lambda stick: stick.centre_x)
        strokes_left_to_right = sorted(strokes_in_word, key=lambda stick: stick.centre_x)

        word_left_x = strokes_left_to_right[0].centre_x
        word_width = strokes_left_to_right[-1].centre_x - word_left_x
        random_generator = random.Random(random_seed)
        edge_flights = []
        for edge, stroke in zip(edges_left_to_right, strokes_left_to_right, strict=True):
            distance_from_centre = math.hypot(edge.centre_x, edge.centre_y) or 1.0
            drift_distance = self._scale_pixels * random_generator.uniform(0.30, 0.55)
            turn_direction = random_generator.choice((-1, 1))
            edge_flights.append(
                EdgeFlight(
                    edge_at_burst=edge,
                    stroke_in_word=stroke,
                    drift_out_x=edge.centre_x / distance_from_centre * drift_distance,
                    drift_out_y=edge.centre_y / distance_from_centre * drift_distance,
                    drift_turn_radians=turn_direction * random_generator.uniform(0.8, 1.8),
                    glide_home_delay_seconds=MAXIMUM_LEFT_TO_RIGHT_STAGGER_SECONDS
                    * (stroke.centre_x - word_left_x)
                    / word_width,
                )
            )
        return edge_flights


def _cube_spin_radians(elapsed_seconds: float) -> float:
    spin_up_seconds = clamp(elapsed_seconds - FINAL_LANDING_SECONDS, 0, SPIN_DURATION_SECONDS)
    spin_acceleration = CUBE_PEAK_SPIN_RADIANS_PER_SECOND / SPIN_DURATION_SECONDS
    return (
        CUBE_INITIAL_SPIN_RADIANS
        + CUBE_IDLE_SPIN_RADIANS_PER_SECOND * elapsed_seconds
        + 0.5 * spin_acceleration * spin_up_seconds**2
    )


def _vertical_squash(elapsed_seconds: float) -> float:
    """1 normally; dips briefly (a Gaussian pulse) at each landing."""
    landing_times = (FIRST_LANDING_SECONDS, SECOND_LANDING_SECONDS, FINAL_LANDING_SECONDS)
    total_squash = sum(
        squash_amount
        * math.exp(-(((elapsed_seconds - landing_seconds) / SQUASH_DURATION_SECONDS) ** 2))
        for landing_seconds, squash_amount in zip(
            landing_times, SQUASH_AMOUNT_AT_EACH_LANDING, strict=True
        )
    )
    return 1 - total_squash


def _edge_in_flight(edge_flight: EdgeFlight, seconds_since_burst: float) -> Stick:
    edge = edge_flight.edge_at_burst
    stroke = edge_flight.stroke_in_word
    drift_progress = ease_out_cubic(seconds_since_burst / EDGE_DRIFT_OUT_SECONDS)
    glide_home_progress = smootherstep(
        (seconds_since_burst - EDGE_GLIDE_HOME_DELAY_SECONDS - edge_flight.glide_home_delay_seconds)
        / EDGE_GLIDE_HOME_SECONDS
    )

    drifted_x = edge.centre_x + edge_flight.drift_out_x * drift_progress
    drifted_y = edge.centre_y + edge_flight.drift_out_y * drift_progress
    drifted_angle = edge.angle_radians + edge_flight.drift_turn_radians * drift_progress

    # Lines have no direction, so turn toward the stroke the short way (within ±90°).
    shortest_turn_to_stroke = (
        stroke.angle_radians - drifted_angle + math.pi / 2
    ) % math.pi - math.pi / 2
    return Stick(
        centre_x=lerp(drifted_x, stroke.centre_x, glide_home_progress),
        centre_y=lerp(drifted_y, stroke.centre_y, glide_home_progress),
        angle_radians=drifted_angle + shortest_turn_to_stroke * glide_home_progress,
        length=lerp(edge.length, stroke.length, glide_home_progress),
    )
