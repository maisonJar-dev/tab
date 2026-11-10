from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QShowEvent, QTextBlockFormat, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from tab.widgets.theme_colors import raise_if_theme_colors_missing, theme_color_property
from tab.widgets.themed_icon_button import ThemedIconButton
from tab.widgets.view_icons import paint_info_icon

INFO_BUTTON_ICON_SIZE_PIXELS = 24  # same as the Profile button
INFO_ARTICLE_DIALOG_WIDTH_PIXELS = 620
INFO_ARTICLE_DIALOG_HEIGHT_PIXELS = 640
# Markdown's headings sit tight on the text above; this gives each section room to breathe.
SPACE_ABOVE_SECTION_HEADING_PIXELS = 18


def create_info_button(article_title: str, article_path: Path, parent: QWidget) -> ThemedIconButton:
    """An "i" (#info_button) that opens `article_path` in an InfoArticleDialog. The parent
    positions it; it floats over the parent's layout."""
    if not article_path.is_file():
        raise FileNotFoundError(f"Info article missing: {article_path}")
    info_button = ThemedIconButton(
        f"About {article_title[0].lower()}{article_title[1:]}",
        paint_info_icon,
        INFO_BUTTON_ICON_SIZE_PIXELS,
        is_checkable=False,
    )
    info_button.setObjectName("info_button")
    info_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
    info_button.setParent(parent)
    info_button.clicked.connect(
        lambda: InfoArticleDialog(article_title, article_path, parent).exec()
    )
    return info_button


class InfoArticleDialog(QDialog):
    """A scrollable short read from a Markdown file in assets/. Esc or Close shuts it.
    Headings take `headingColor` from theme.qss (baby blue, like the callout card titles)."""

    headingColor = theme_color_property("_heading_color")

    def __init__(self, article_title: str, article_path: Path, parent: QWidget) -> None:
        super().__init__(parent)
        self._heading_color = QColor()
        self.setObjectName("info_article_dialog")
        self.setWindowTitle(article_title)
        self.setModal(True)
        self.resize(INFO_ARTICLE_DIALOG_WIDTH_PIXELS, INFO_ARTICLE_DIALOG_HEIGHT_PIXELS)

        self._article_view = article_view = QTextBrowser()
        article_view.setObjectName("info_article")
        article_view.setMarkdown(article_path.read_text(encoding="utf-8"))
        article_view.document().setDocumentMargin(4)

        close_button = QPushButton("Close")
        close_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        close_button.clicked.connect(self.accept)
        button_row_layout = QHBoxLayout()
        button_row_layout.addStretch()
        button_row_layout.addWidget(close_button)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(24, 20, 24, 20)
        dialog_layout.setSpacing(12)
        dialog_layout.addWidget(article_view, stretch=1)
        dialog_layout.addLayout(button_row_layout)
        article_view.setFocus()  # arrow keys and Page Up/Down scroll straight away

    def showEvent(self, show_event: QShowEvent) -> None:
        # theme.qss colours arrive at polish, after __init__, so headings are styled here.
        raise_if_theme_colors_missing(self, ["headingColor"])
        self._format_headings()
        super().showEvent(show_event)

    def _format_headings(self) -> None:
        article_block = self._article_view.document().begin()
        while article_block.isValid():
            heading_level = article_block.blockFormat().headingLevel()
            if heading_level > 0:
                heading_cursor = QTextCursor(article_block)
                heading_cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                heading_char_format = QTextCharFormat()
                heading_char_format.setForeground(self._heading_color)
                heading_cursor.mergeCharFormat(heading_char_format)
                heading_block_format = QTextBlockFormat()
                is_section_heading = heading_level > 1
                heading_block_format.setTopMargin(
                    SPACE_ABOVE_SECTION_HEADING_PIXELS if is_section_heading else 0
                )
                heading_cursor.mergeBlockFormat(heading_block_format)
            article_block = article_block.next()
