from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from tab.core.timer import SESSION_RATINGS
from tab.widgets.themed_icon_button import ThemedIconButton
from tab.widgets.view_icons import paint_close_icon

SKIP_BUTTON_ICON_SIZE_PIXELS = 14


class SessionRatingRow(QWidget):
    """The rating prompt, one chip per SESSION_RATINGS value, and a small × at the prompt's
    top left to skip rating.

    Keeps its space while hidden, so the controls above it don't jump when it appears.
    The owner shows it while the timer awaits a rating and passes `rating_chosen` and
    `rating_skipped` on.
    """

    rating_chosen = Signal(int)
    rating_skipped = Signal()

    def __init__(self, horizontal_inset_pixels: int) -> None:
        super().__init__()
        session_rating_size_policy = self.sizePolicy()
        session_rating_size_policy.setRetainSizeWhenHidden(True)
        self.setSizePolicy(session_rating_size_policy)

        session_rating_prompt = QLabel("Rate that session's impact")
        session_rating_prompt.setObjectName("session_rating_prompt")
        session_rating_prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        session_rating_prompt.setWordWrap(True)  # the Timer's column is narrow: two lines there
        skip_rating_button = ThemedIconButton(
            "Skip rating", paint_close_icon, SKIP_BUTTON_ICON_SIZE_PIXELS, is_checkable=False
        )
        skip_rating_button.setObjectName("session_rating_skip_button")
        skip_rating_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        skip_rating_button.clicked.connect(self.rating_skipped.emit)
        # × | prompt | an empty column as wide as the ×: the prompt stays centred over the chips
        # without the × ever covering it.
        prompt_row_layout = QHBoxLayout()
        prompt_row_layout.setSpacing(0)
        prompt_row_layout.addWidget(
            skip_rating_button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        prompt_row_layout.addWidget(session_rating_prompt, stretch=1)
        prompt_row_layout.addSpacing(skip_rating_button.sizeHint().width())

        rating_button_row_layout = QHBoxLayout()
        rating_button_row_layout.setSpacing(6)
        for rating in SESSION_RATINGS:
            rating_button = QPushButton(str(rating))
            rating_button.setObjectName("session_rating_button")
            rating_button.setAccessibleName(f"Rate session {rating}")
            rating_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            rating_button.setCursor(Qt.CursorShape.PointingHandCursor)
            rating_button.clicked.connect(
                lambda _checked=False, rating=rating: self.rating_chosen.emit(rating)
            )
            rating_button_row_layout.addWidget(rating_button)

        session_rating_layout = QVBoxLayout(self)
        session_rating_layout.setContentsMargins(
            horizontal_inset_pixels, 16, horizontal_inset_pixels, 0
        )
        session_rating_layout.setSpacing(8)
        session_rating_layout.addLayout(prompt_row_layout)
        session_rating_layout.addLayout(rating_button_row_layout)
