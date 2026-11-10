from typing import NamedTuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from tab.widgets.callout_card import (
    create_callout_card,
    create_callout_card_row,
    create_callout_card_title,
)


class Shortcut(NamedTuple):
    action: str
    # Keys pressed together are joined by "+"; alternatives are separated by " / ".
    keys: str


SHORTCUT_GROUPS_BY_COLUMN: list[list[tuple[str, list[Shortcut]]]] = [
    [
        (
            "Anywhere",
            [
                Shortcut("View switcher", "Tab"),
                Shortcut("Shortcuts (this page)", "Ctrl+S"),
                Shortcut("Profile", "Ctrl+P"),
                Shortcut("Start / pause timer", "Space"),
                Shortcut("Next control", "Ctrl+Tab"),
                Shortcut("Previous control", "Ctrl+Shift+Tab"),
            ],
        ),
        (
            "View switcher",
            [
                Shortcut("Move highlight", "Arrows / Ctrl+Tab"),
                Shortcut("Choose", "Enter"),
                Shortcut("Choose if moved, else close", "Tab"),
                Shortcut("Close", "Esc"),
            ],
        ),
        (
            "Start-up",
            [Shortcut("Skip the intro", "Tab / Space / Enter")],
        ),
    ],
    [
        (
            "Focused controls",
            [
                Shortcut("Press button", "Space"),
                Shortcut("Turn a wheel or drum", "↑ / ↓ / Scroll"),
            ],
        ),
        (
            "Duration knot (paused)",
            [
                Shortcut("Turn it", "Drag"),
                Shortcut("Set it spinning", "Flick"),
                Shortcut("Stop it", "Click"),
            ],
        ),
        (
            "Info articles",
            [
                Shortcut("Scroll", "↑ / ↓"),
                Shortcut("Page", "PgUp / PgDn"),
                Shortcut("Close", "Esc"),
            ],
        ),
    ],
]


class ShortcutsView(QWidget):
    """Every keyboard shortcut and knot gesture, as callout cards in two columns.

    Not in the switcher: opened with Ctrl+S (which also closes it) or the Shortcuts button
    in Settings. The list is written out by hand, so a new key binding must be added here too.
    """

    def __init__(self) -> None:
        super().__init__()
        columns_layout = QHBoxLayout(self)
        columns_layout.setContentsMargins(32, 32, 32, 32)
        columns_layout.setSpacing(12)
        for column_groups in SHORTCUT_GROUPS_BY_COLUMN:
            column_layout = QVBoxLayout()
            column_layout.setSpacing(12)
            for group_title, shortcuts in column_groups:
                column_layout.addWidget(_create_shortcut_card(group_title, shortcuts))
            column_layout.addStretch(1)
            columns_layout.addLayout(column_layout)
        columns_layout.addStretch(1)  # cards keep their width; spare room goes to the right


def _create_shortcut_card(group_title: str, shortcuts: list[Shortcut]) -> QWidget:
    card_layout = QVBoxLayout()
    card_layout.setSpacing(10)
    card_layout.addWidget(create_callout_card_title(group_title))
    for shortcut in shortcuts:
        card_layout.addLayout(
            create_callout_card_row(QLabel(shortcut.action), _create_keycaps(shortcut.keys))
        )
    return create_callout_card(card_layout)


def _create_keycaps(keys: str) -> QWidget:
    """ "Ctrl+Shift+Tab / Esc" → [Ctrl]+[Shift]+[Tab] / [Esc] as small keycap labels."""
    keycaps = QWidget()
    keycaps_layout = QHBoxLayout(keycaps)
    keycaps_layout.setContentsMargins(0, 0, 0, 0)
    keycaps_layout.setSpacing(4)
    for alternative_index, key_combination in enumerate(keys.split(" / ")):
        if alternative_index:
            keycaps_layout.addWidget(_create_keycap_separator("/"))
        for key_index, key_name in enumerate(key_combination.split("+")):
            if key_index:
                keycaps_layout.addWidget(_create_keycap_separator("+"))
            keycap = QLabel(key_name)
            keycap.setObjectName("shortcut_keycap")
            keycap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            keycaps_layout.addWidget(keycap)
    return keycaps


def _create_keycap_separator(separator_text: str) -> QLabel:
    separator = QLabel(separator_text)
    separator.setObjectName("shortcut_keycap_separator")
    return separator
