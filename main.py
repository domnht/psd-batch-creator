import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from ui.main_window import MainWindow

def getResourcePath(relativePath: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relativePath
    return Path(__file__).resolve().parent / relativePath

def loadStyleSheet(application: QApplication, styleFile: str = "assets/style.qss") -> None:
    stylePath = getResourcePath(styleFile)
    if not stylePath.exists(): return
    application.setStyleSheet(stylePath.read_text(encoding="utf-8"))

def main() -> int:
    application = QApplication(sys.argv)
    loadStyleSheet(application)
    appIconPath = getResourcePath("assets/app_icon.png")
    if appIconPath.exists():
        application.setWindowIcon(QIcon(str(appIconPath)))
    window = MainWindow()
    window.setWindowIcon(application.windowIcon())
    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
