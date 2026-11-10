import math

import pytest

from tab.core.knot_animation import (
    DOT_COUNT,
    FACE_ON_ORIENTATION,
    HELD_STILL_BEFORE_RELEASE_SECONDS,
    LARGEST_RUNNING_DOT_RADIUS,
    SOLID_TUBE_RADIUS,
    SOLIDIFY_SECONDS,
    KnotAnimationState,
    knot_dots,
    rotation_about_axis,
)

TILTED_AXES = [(0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.4, 0.7, 0.6), (1.0, -1.0, 0.3)]


@pytest.mark.parametrize("rotation_radians", [0.0, 1.0, math.pi / 2, 2.5, math.pi])
@pytest.mark.parametrize("axis", TILTED_AXES)
def test_solid_knot_is_one_gapless_tube_at_every_angle(
    axis: tuple[float, float, float], rotation_radians: float
) -> None:
    dots = knot_dots(0.3, 1.0, rotation_about_axis(axis, rotation_radians), solidity=1.0)
    assert all(dot.radius == pytest.approx(SOLID_TUBE_RADIUS) for dot in dots)
    neighbour_gaps = [
        math.dist((dot.x, dot.y), (next_dot.x, next_dot.y))
        for dot, next_dot in zip(dots, dots[1:] + dots[:1], strict=True)
    ]
    # Spacing well under a radius leaves only a sub-pixel scallop along the tube's edge.
    assert max(neighbour_gaps) < SOLID_TUBE_RADIUS / 2


def test_running_dots_vary_in_size() -> None:
    radii = [dot.radius for dot in knot_dots(0.0, 0.0, FACE_ON_ORIENTATION, solidity=0.0)]
    assert max(radii) <= LARGEST_RUNNING_DOT_RADIUS
    assert max(radii) > 2 * min(radii)


@pytest.mark.parametrize("solidity", [0.0, 0.5, 1.0])
def test_knot_fits_the_drawing_area_at_every_angle(solidity: float) -> None:
    for wobble_radians in (0.0, math.pi / 2, math.pi):
        for axis in TILTED_AXES:
            orientation = rotation_about_axis(axis, 2.0)
            dots = knot_dots(0.17, wobble_radians, orientation, solidity)
            for dot in dots:
                assert abs(dot.x) + dot.radius <= 1.0
                assert abs(dot.y) + dot.radius <= 1.0
            # Depth is stretched to the full range each frame, so shading keeps its contrast.
            assert min(dot.depth for dot in dots) == pytest.approx(-1.0)
            assert max(dot.depth for dot in dots) == pytest.approx(1.0)


def test_rotation_is_right_handed_and_a_full_turn_comes_back() -> None:
    quarter_turn_about_y = rotation_about_axis((0.0, 2.0, 0.0), math.pi / 2)
    rotated_x_axis = [row[0] for row in quarter_turn_about_y]  # where (1, 0, 0) ends up
    assert rotated_x_axis == pytest.approx([0.0, 0.0, -1.0], abs=1e-12)
    full_turn = rotation_about_axis((0.4, 0.7, 0.6), 2 * math.pi)
    for row, face_on_row in zip(full_turn, FACE_ON_ORIENTATION, strict=True):
        assert row == pytest.approx(face_on_row, abs=1e-12)


def test_rejects_a_rotation_axis_without_direction() -> None:
    with pytest.raises(ValueError, match="zero vector"):
        rotation_about_axis((0.0, 0.0, 0.0), 1.0)


def test_dots_flow_round_a_closed_loop() -> None:
    start_dots = knot_dots(0.0, 0.0, FACE_ON_ORIENTATION, solidity=1.0)
    assert knot_dots(0.01, 0.0, FACE_ON_ORIENTATION, solidity=1.0)[0] != start_dots[0]
    one_dot_further = knot_dots(1 / DOT_COUNT, 0.0, FACE_ON_ORIENTATION, solidity=1.0)
    assert one_dot_further[0].x == pytest.approx(start_dots[1].x)
    assert one_dot_further[0].y == pytest.approx(start_dots[1].y)


def test_rejects_solidity_outside_zero_to_one() -> None:
    with pytest.raises(ValueError, match="1.5"):
        knot_dots(0.0, 0.0, FACE_ON_ORIENTATION, solidity=1.5)


def test_running_loosens_and_flows_then_pausing_solidifies_and_stops() -> None:
    animation_state = KnotAnimationState()
    assert animation_state.is_settled

    animation_state.advance(SOLIDIFY_SECONDS, is_timer_running=True)
    assert animation_state.solidity == 0.0
    flow_before = animation_state.flow_laps
    orientation_before = animation_state.orientation
    animation_state.advance(1.0, is_timer_running=True)
    assert animation_state.flow_laps > flow_before
    assert animation_state.orientation != orientation_before
    assert not animation_state.is_settled

    animation_state.advance(SOLIDIFY_SECONDS, is_timer_running=False)
    assert animation_state.is_settled
    frozen_flow = animation_state.flow_laps
    frozen_orientation = animation_state.orientation
    animation_state.advance(5.0, is_timer_running=False)
    assert animation_state.flow_laps == frozen_flow
    assert animation_state.orientation == frozen_orientation


def test_stays_solid_while_paused() -> None:
    animation_state = KnotAnimationState()
    animation_state.advance(10.0, is_timer_running=False)
    assert animation_state.is_settled
    assert animation_state.flow_laps == 0.0


def test_rejects_time_going_backwards() -> None:
    with pytest.raises(ValueError, match="-1"):
        KnotAnimationState().advance(-1.0, is_timer_running=True)


def _paused_state() -> KnotAnimationState:
    return KnotAnimationState()  # starts paused: solid and still


def _grabbed_paused_state() -> KnotAnimationState:
    animation_state = _paused_state()
    animation_state.grab()
    return animation_state


def test_dragging_right_moves_the_front_of_the_knot_right() -> None:
    animation_state = _grabbed_paused_state()
    dots_before = animation_state.dots()
    front_dot_index = max(range(DOT_COUNT), key=lambda dot_index: dots_before[dot_index].depth)
    animation_state.turn_by_drag(0.05, 0.0, 0.016)
    assert animation_state.dots()[front_dot_index].x > dots_before[front_dot_index].x


def test_dragging_down_moves_the_front_of_the_knot_down() -> None:
    animation_state = _grabbed_paused_state()
    dots_before = animation_state.dots()
    front_dot_index = max(range(DOT_COUNT), key=lambda dot_index: dots_before[dot_index].depth)
    animation_state.turn_by_drag(0.0, 0.05, 0.016)
    assert animation_state.dots()[front_dot_index].y > dots_before[front_dot_index].y


def test_a_flick_coasts_then_slows_to_a_stop() -> None:
    animation_state = _grabbed_paused_state()
    for _ in range(5):
        animation_state.turn_by_drag(0.06, 0.02, 0.016)
    animation_state.release_drag(0.01)
    assert not animation_state.is_settled
    orientation_at_release = animation_state.orientation
    animation_state.advance(0.1, is_timer_running=False)
    assert animation_state.orientation != orientation_at_release

    for _ in range(30 * 20):
        animation_state.advance(1 / 30, is_timer_running=False)
    assert animation_state.is_settled
    stopped_orientation = animation_state.orientation
    animation_state.advance(1.0, is_timer_running=False)
    assert animation_state.orientation == stopped_orientation


def test_letting_go_after_holding_still_drops_without_coasting() -> None:
    animation_state = _grabbed_paused_state()
    animation_state.turn_by_drag(0.06, 0.0, 0.016)
    animation_state.release_drag(HELD_STILL_BEFORE_RELEASE_SECONDS * 2)
    assert animation_state.is_settled


def test_the_knot_does_not_coast_while_still_held() -> None:
    animation_state = _grabbed_paused_state()
    animation_state.turn_by_drag(0.06, 0.0, 0.016)
    held_orientation = animation_state.orientation
    animation_state.advance(0.5, is_timer_running=False)
    assert animation_state.orientation == held_orientation


def test_starting_the_timer_cancels_a_coast() -> None:
    animation_state = _grabbed_paused_state()
    animation_state.turn_by_drag(0.06, 0.0, 0.016)
    animation_state.release_drag(0.0)
    animation_state.advance(0.01, is_timer_running=True)
    animation_state.advance(SOLIDIFY_SECONDS * 2, is_timer_running=False)
    assert animation_state.is_settled


def test_grabbing_a_coasting_knot_stops_it() -> None:
    animation_state = _grabbed_paused_state()
    for _ in range(5):
        animation_state.turn_by_drag(0.06, 0.0, 0.016)
    animation_state.release_drag(0.0)
    animation_state.grab()
    animation_state.release_drag(0.0)  # a quick tap: no movement in between
    assert animation_state.is_settled


def test_rejects_dragging_without_grabbing_first() -> None:
    with pytest.raises(ValueError, match="grabbed"):
        _paused_state().turn_by_drag(0.01, 0.0, 0.016)


def test_rejects_drag_steps_back_in_time() -> None:
    with pytest.raises(ValueError, match="-0.1"):
        _grabbed_paused_state().turn_by_drag(0.01, 0.0, -0.1)
