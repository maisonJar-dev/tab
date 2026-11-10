from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLayout, QWidget

CALLOUT_CARD_WIDTH_PIXELS = 360


def create_callout_card(card_content_layout: QLayout) -> QFrame:
    """A solid rounded card (#callout_card) that separates a group from the wall behind it."""
    callout_card = QFrame()
    callout_card.setObjectName("callout_card")
    callout_card.setFixedWidth(CALLOUT_CARD_WIDTH_PIXELS)
    callout_card.setLayout(card_content_layout)
    card_content_layout.setContentsMargins(20, 14, 20, 14)
    return callout_card


def create_callout_card_title(card_title: str) -> QLabel:
    callout_card_title_label = QLabel(card_title)
    callout_card_title_label.setObjectName("callout_card_title")
    return callout_card_title_label


def create_callout_card_row(left_widget: QWidget, right_widget: QWidget) -> QHBoxLayout:
    """One card row: a label or title on the left, its value or control pushed to the right."""
    row_layout = QHBoxLayout()
    row_layout.addWidget(left_widget)
    row_layout.addStretch()
    row_layout.addWidget(right_widget)
    return row_layout
