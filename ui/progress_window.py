from pathlib import Path
from utils.widget_utils import WidgetUtils
from PyQt6.QtCore import QPropertyAnimation, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class ProgressWindow(QDialog):
    cancelRequested = pyqtSignal()
    openFolderRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.isCancellationRequested = False
        self.isFinished = False
        self.outputDirectory = None

        self.setWindowTitle("Batch Creation Progress")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self._createWidgets()
        self._createLayout()
        self._connectSignals()

    def _createWidgets(self) -> None:
        self.statusLabel = QLabel("Preparing...")

        self.progressBar = QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)

        self.progressAnimation = QPropertyAnimation(
            self.progressBar,
            b"value",
            self,
        )
        self.progressAnimation.setDuration(250)

        self.logTextEdit = QTextEdit()
        self.logTextEdit.setReadOnly(True)
        self.logTextEdit.setProperty("class", "codeArea")
        WidgetUtils.scaleFont(self.logTextEdit, 0.95)

        self.openFolderButton = QPushButton("Open Folder")
        self.openFolderButton.setVisible(False)

        self.cancelButton = QPushButton("Cancel")

    def _createLayout(self) -> None:
        buttonLayout = QHBoxLayout()
        buttonLayout.setSpacing(5)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self.openFolderButton)
        buttonLayout.addWidget(self.cancelButton)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.statusLabel)
        mainLayout.addWidget(self.progressBar)
        mainLayout.addWidget(QLabel("Log:"))
        mainLayout.addWidget(self.logTextEdit)
        mainLayout.addLayout(buttonLayout)

        self.setLayout(mainLayout)

    def _connectSignals(self) -> None:
        self.cancelButton.clicked.connect(self.handleCancelOrCloseButtonClicked)
        self.openFolderButton.clicked.connect(self.openFolderRequested.emit)

    def setOutputDirectory(self, outputDirectory: str | Path) -> None:
        self.outputDirectory = Path(outputDirectory)

    def handleCancelOrCloseButtonClicked(self) -> None:
        if self.isFinished:
            self.accept()
            return

        self.requestCancel()

    def requestCancel(self) -> None:
        if self.isCancellationRequested:
            return

        reply = QMessageBox.question(
            self,
            "Cancel Batch Creation",
            "Do you want to cancel the batch creation process?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.isCancellationRequested = True
        self.cancelButton.setEnabled(False)
        self.statusLabel.setText("Cancelling after the current file...")
        self.appendLog("Cancellation requested. The current file will finish first.")

        self.cancelRequested.emit()

    def updateProgress(self, currentValue: int, totalValue: int) -> None:
        if totalValue <= 0:
            self._animateProgressBar(0)
            self.statusLabel.setText("No files to create.")
            return

        percentValue = int(currentValue / totalValue * 100)

        self._animateProgressBar(percentValue)
        self.statusLabel.setText(
            f"Creating files: {currentValue}/{totalValue} ({percentValue}%)"
        )

    def _animateProgressBar(self, targetValue: int) -> None:
        targetValue = max(0, min(100, targetValue))

        self.progressAnimation.stop()
        self.progressAnimation.setStartValue(self.progressBar.value())
        self.progressAnimation.setEndValue(targetValue)
        self.progressAnimation.start()

    def appendLog(self, message: str) -> None:
        self.logTextEdit.append(message)

    def showSuccessMessage(self) -> None:
        QMessageBox.information(
            self,
            "Batch Creation Completed",
            "Batch PSD creation has completed successfully.",
        )

    def markFinished(self, wasCancelled: bool) -> None:
        self.isFinished = True
        self.isCancellationRequested = False

        if wasCancelled:
            self.statusLabel.setText("Batch creation cancelled.")
            self.openFolderButton.setVisible(False)
        else:
            self._animateProgressBar(100)
            self.statusLabel.setText("Batch creation completed.")
            self.openFolderButton.setVisible(True)

        self.cancelButton.setEnabled(True)
        self.cancelButton.setText("Close")

    def closeEvent(self, event) -> None:
        if self.isFinished:
            event.accept()
            return

        reply = QMessageBox.question(
            self,
            "Cancel Batch Creation",
            "The batch creation process is still running. Do you want to cancel it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            event.ignore()
            return

        self.requestCancel()
        event.ignore()