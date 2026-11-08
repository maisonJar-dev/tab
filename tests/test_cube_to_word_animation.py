import math

import pytest

from tab.core.cube_to_word_animation import (
    ASSEMBLE_START_SECONDS,
    CUBE_EDGES,
    FIRST_LANDING_SECONDS,
    TAB_WORD_STROKES,
    TOTAL_DURATION_SECONDS,
    CubeToWordAnimation,
    animation_scale_for_viewport,
    smootherstep,
)

SCALE_PIXELS = 100.0
VIEWPORT_HEIGHT_PIXELS = 600.0
POSITION_TOLERANCE_PIXELS = 1e-6


def create_animation() -> CubeToWordAnimation:
    return CubeToWordAnimation(
        scale_pixels=SCALE_PIXELS, viewport_height_pixels=VIEWPORT_HEIGHT_PIXELS
    )


def all_points(line_segments):
    return [point for segment in line_segments for point in segment]


def points_are_close(first_point, second_point, tolerance_pixels: float) -> bool:
    return all(
        math.isclose(first, second, abs_tol=tolerance_pixels)
        for first, second in zip(first_point, second_point, strict=True)
    )


def segments_are_close(first_segment, second_segment, tolerance_pixels: float) -> bool:
    """Lines have no direction: a segment matches its reverse."""
    (first_start, first_end), (second_start, second_end) = first_segment, second_segment
    same_direction = points_are_close(
        first_start, second_start, tolerance_pixels
    ) and points_are_close(first_end, second_end, tolerance_pixels)
    reversed_direction = points_are_close(
        first_start, second_end, tolerance_pixels
    ) and points_are_close(first_end, second_start, tolerance_pixels)
    return same_direction or reversed_direction


def assert_same_undirected_segments(
    actual_segments, expected_segments, tolerance_pixels: float = POSITION_TOLERANCE_PIXELS
) -> None:
    """Order and direction don't matter: every actual segment must pair off with an expected one."""
    unmatched_expected_segments = list(expected_segments)
    assert len(actual_segments) == len(unmatched_expected_segments)
    for actual_segment in actual_segments:
        matching_index = next(
            (
                index
                for index, expected_segment in enumerate(unmatched_expected_segments)
                if segments_are_close(actual_segment, expected_segment, tolerance_pixels)
            ),
            None,
        )
        assert matching_index is not None, f"No expected segment matches {actual_segment}"
        unmatched_expected_segments.pop(matching_index)


def test_every_cube_edge_becomes_exactly_one_stroke_of_the_word() -> None:
    assert len(CUBE_EDGES) == 12
    assert len(TAB_WORD_STROKES) == len(CUBE_EDGES)


def test_smootherstep_eases_from_zero_to_one_and_clamps() -> None:
    assert smootherstep(-1.0) == 0.0
    assert smootherstep(0.0) == 0.0
    assert smootherstep(0.5) == pytest.approx(0.5)
    assert smootherstep(1.0) == 1.0
    assert smootherstep(2.0) == 1.0


def test_scale_follows_the_smaller_viewport_dimension_with_a_floor() -> None:
    assert animation_scale_for_viewport(1000, 2000) == pytest.approx(260)
    assert animation_scale_for_viewport(2000, 500) == pytest.approx(200)
    assert animation_scale_for_viewport(10, 10) == 40


def test_cube_starts_entirely_above_the_window() -> None:
    lowest_point_y = max(y for _, y in all_points(create_animation().line_segments_at(0.0)))
    assert lowest_point_y < -VIEWPORT_HEIGHT_PIXELS / 2


def test_cube_rests_on_the_ground_at_first_landing() -> None:
    animation = create_animation()
    landing_segments = animation.line_segments_at(FIRST_LANDING_SECONDS)
    lowest_point_y = max(y for _, y in all_points(landing_segments))
    assert lowest_point_y == pytest.approx(animation.ground_y_pixels)


def test_cube_is_centred_when_it_breaks_apart() -> None:
    burst_points = all_points(create_animation().line_segments_at(ASSEMBLE_START_SECONDS))
    centroid_x = sum(x for x, _ in burst_points) / len(burst_points)
    centroid_y = sum(y for _, y in burst_points) / len(burst_points)
    # Not exactly 0: perspective draws the nearer corners slightly larger.
    visually_centred_tolerance_pixels = 0.5
    assert centroid_x == pytest.approx(0, abs=visually_centred_tolerance_pixels)
    assert centroid_y == pytest.approx(0, abs=visually_centred_tolerance_pixels)


def test_edges_do_not_jump_when_the_cube_breaks_apart() -> None:
    animation = create_animation()
    assert_same_undirected_segments(
        animation.line_segments_at(ASSEMBLE_START_SECONDS - 1e-9),
        animation.line_segments_at(ASSEMBLE_START_SECONDS),
        tolerance_pixels=1e-4,
    )


def test_ends_exactly_on_the_word_and_stays_there() -> None:
    animation = create_animation()
    assert_same_undirected_segments(
        animation.line_segments_at(TOTAL_DURATION_SECONDS), animation.word_segments
    )
    assert_same_undirected_segments(
        animation.line_segments_at(TOTAL_DURATION_SECONDS + 60), animation.word_segments
    )


def test_word_is_centred_on_the_origin() -> None:
    word_points = all_points(create_animation().word_segments)
    xs = [x for x, _ in word_points]
    ys = [y for _, y in word_points]
    assert (min(xs) + max(xs)) / 2 == pytest.approx(0)
    assert (min(ys) + max(ys)) / 2 == pytest.approx(0)


def test_same_inputs_give_the_same_frames() -> None:
    sample_time_seconds = ASSEMBLE_START_SECONDS + 0.5
    assert create_animation().line_segments_at(sample_time_seconds) == (
        create_animation().line_segments_at(sample_time_seconds)
    )


def test_stroke_width_scales_with_the_animation() -> None:
    small = CubeToWordAnimation(scale_pixels=100, viewport_height_pixels=600)
    large = CubeToWordAnimation(scale_pixels=200, viewport_height_pixels=600)
    assert large.stroke_width_pixels == pytest.approx(2 * small.stroke_width_pixels)
