from PySide6.QtCore import Property
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget


def theme_color_property(private_attribute_name: str) -> Property:
    """A QColor Qt property, so theme.qss can set it with `qproperty-<name>: #hex;`.

    The owning widget must initialise `private_attribute_name` to QColor() (invalid).
    """

    def get_color(widget: QWidget) -> QColor:
        return getattr(widget, private_attribute_name)

    def set_color(widget: QWidget, color: QColor) -> None:
        setattr(widget, private_attribute_name, QColor(color))
        widget.update()

    return Property(QColor, get_color, set_color)


def raise_if_theme_colors_missing(widget: QWidget, color_property_names: list[str]) -> None:
    missing_property_names = [
        property_name
        for property_name in color_property_names
        if not widget.property(property_name).isValid()
    ]
    if missing_property_names:
        missing_qss_lines = ", ".join(f"qproperty-{name}" for name in missing_property_names)
        raise RuntimeError(f"#{widget.objectName()} in theme.qss is missing: {missing_qss_lines}")
