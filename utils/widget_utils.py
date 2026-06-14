from PyQt6.QtWidgets import (
    QWidget
)

class WidgetUtils:
    
    @staticmethod
    def scaleFont(widget: QWidget, factor: float) -> None:
        currentFont = widget.font()
        newSize = int(currentFont.pointSize() * factor)
        currentFont.setPointSize(newSize)
        widget.setFont(currentFont)
