from pathlib import Path
import csv
import io

from PyQt6.QtCore import QSettings, QThread, Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.progress_window import ProgressWindow
from utils.psd_task import (
    DEFAULT_HEIGHT,
    DEFAULT_RESOLUTION,
    DEFAULT_WIDTH,
    PsdTask,
    createTaskFromTableRow,
    createTaskFromTextLine,
)
from utils.widget_utils import WidgetUtils
from workers.psd_batch_worker import PsdBatchWorker


class MainWindow(QMainWindow):
    COLUMN_SUB_DIRECTORY = 0
    COLUMN_FILE_NAME = 1
    COLUMN_BACKGROUND_COLOR = 2
    COLUMN_WIDTH = 3
    COLUMN_HEIGHT = 4
    COLUMN_RESOLUTION = 5

    TABLE_HEADERS = [
        "Sub directory",
        "File name",
        "Background color",
        "Width",
        "Height",
        "Resolution",
    ]

    REQUIRED_TABLE_HEADERS = [
        "File name",
        "Background color",
        "Width",
        "Height",
        "Resolution",
    ]

    SETTINGS_ORGANIZATION = "NguyenHieuThanh"
    SETTINGS_APPLICATION = "PsdBatchCreator"

    SETTINGS_WINDOW_GEOMETRY = "mainWindowGeometry"
    SETTINGS_OUTPUT_DIRECTORY = "outputDirectory"

    DEFAULT_WINDOW_WIDTH = 800
    DEFAULT_WINDOW_HEIGHT = 500

    def __init__(self):
        super().__init__()

        self.workerThread = None
        self.worker = None
        self.progressWindow = None

        self.settings = QSettings(
            self.SETTINGS_ORGANIZATION,
            self.SETTINGS_APPLICATION,
        )

        self.setWindowTitle("PSD Batch Creator")

        self._createWidgets()
        self._createLayout()
        self._connectSignals()
        self._restoreSettings()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _createWidgets(self) -> None:
        self.tabWidget = QTabWidget()

        self.tableTab = QWidget()
        self.textTab = QWidget()

        self.pasteButton = QPushButton("Paste")
        self.clearTableButton = QPushButton("Clear Table")

        self.tableWidget = QTableWidget(0, len(self.TABLE_HEADERS))
        self.tableWidget.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.tableWidget.setAlternatingRowColors(True)
        self.tableWidget.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectItems
        )
        self.tableWidget.setSelectionMode(
            QTableWidget.SelectionMode.ExtendedSelection
        )
        self.tableWidget.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.SelectedClicked
            | QTableWidget.EditTrigger.EditKeyPressed
        )

        horizontalHeader = self.tableWidget.horizontalHeader()
        horizontalHeader.setSectionsMovable(True)
        horizontalHeader.setStretchLastSection(False)
        horizontalHeader.setMinimumSectionSize(80)

        for columnIndex in range(len(self.TABLE_HEADERS)):
            horizontalHeader.setSectionResizeMode(
                columnIndex,
                QHeaderView.ResizeMode.Interactive,
            )

        horizontalHeader.setSectionResizeMode(
            self.COLUMN_FILE_NAME,
            QHeaderView.ResizeMode.Stretch,
        )

        self.tableWidget.setColumnWidth(self.COLUMN_BACKGROUND_COLOR, 110)
        self.tableWidget.setColumnWidth(self.COLUMN_WIDTH, 100)
        self.tableWidget.setColumnWidth(self.COLUMN_HEIGHT, 100)
        self.tableWidget.setColumnWidth(self.COLUMN_RESOLUTION, 120)
        self.tableWidget.setColumnWidth(self.COLUMN_SUB_DIRECTORY, 140)

        self.textInput = QPlainTextEdit()
        self.textInput.setProperty("class", "codeArea")
        self.textInput.setPlaceholderText(
            "#f0f1f2 Poster\n"
            "Animals #010203 Cat\n"
            "Animals #040506 Dog"
        )
        WidgetUtils.scaleFont(self.textInput, 0.95)

        self.textHelpLabel = QLabel(
            f"Default size: {DEFAULT_WIDTH}px x {DEFAULT_HEIGHT}px at "
            f"{DEFAULT_RESOLUTION} ppi"
        )

        self.outputDirectoryLineEdit = QLineEdit()

        self.browseOutputButton = QPushButton("Browse")
        self.startButton = QPushButton("Create Batch Files")
        self.startButton.setProperty("class", "primaryButton")

    def _createLayout(self) -> None:
        tableButtonLayout = QHBoxLayout()
        tableButtonLayout.setSpacing(5)
        tableButtonLayout.addWidget(self.pasteButton)
        tableButtonLayout.addWidget(self.clearTableButton)
        tableButtonLayout.addStretch()

        tableTabLayout = QVBoxLayout()
        tableTabLayout.setContentsMargins(5, 5, 5, 5)
        tableTabLayout.addLayout(tableButtonLayout)
        tableTabLayout.addWidget(self.tableWidget)

        self.tableTab.setLayout(tableTabLayout)

        textTabLayout = QVBoxLayout()
        textTabLayout.setContentsMargins(5, 5, 5, 5)
        textTabLayout.addWidget(self.textHelpLabel)
        textTabLayout.addWidget(self.textInput)

        self.textTab.setLayout(textTabLayout)

        self.tabWidget.addTab(self.tableTab, "Table Input")
        self.tabWidget.addTab(self.textTab, "Text Input")

        outputLayout = QHBoxLayout()
        outputLayout.addWidget(QLabel("Output folder:"))
        outputLayout.addWidget(self.outputDirectoryLineEdit)
        outputLayout.addWidget(self.browseOutputButton)

        commandLayout = QHBoxLayout()
        commandLayout.addStretch()
        commandLayout.addWidget(self.startButton)
        commandLayout.setContentsMargins(0, 0, 0, 15)

        mainLayout = QVBoxLayout()
        mainLayout.setSpacing(5)
        mainLayout.addWidget(self.tabWidget)
        mainLayout.addLayout(outputLayout)
        mainLayout.addLayout(commandLayout)

        centralWidget = QWidget()
        centralWidget.setLayout(mainLayout)

        self.setCentralWidget(centralWidget)

    def _connectSignals(self) -> None:
        self.pasteButton.clicked.connect(self.pasteTableData)
        self.clearTableButton.clicked.connect(self.clearTable)
        self.browseOutputButton.clicked.connect(self.browseOutputDirectory)
        self.startButton.clicked.connect(self.startBatchCreation)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _restoreSettings(self) -> None:
        savedGeometry = self.settings.value(self.SETTINGS_WINDOW_GEOMETRY)

        if savedGeometry is not None:
            self.restoreGeometry(savedGeometry)
        else:
            self.resize(self.DEFAULT_WINDOW_WIDTH, self.DEFAULT_WINDOW_HEIGHT)

        savedOutputDirectory = self.settings.value(
            self.SETTINGS_OUTPUT_DIRECTORY,
            str(Path.cwd() / "output"),
        )

        self.outputDirectoryLineEdit.setText(str(savedOutputDirectory))

    def _saveSettings(self) -> None:
        self.settings.setValue(
            self.SETTINGS_WINDOW_GEOMETRY,
            self.saveGeometry(),
        )

        self.settings.setValue(
            self.SETTINGS_OUTPUT_DIRECTORY,
            self.outputDirectoryLineEdit.text().strip(),
        )

    # ------------------------------------------------------------------
    # Table input
    # ------------------------------------------------------------------

    def pasteTableData(self) -> None:
        clipboardText = QApplication.clipboard().text()

        if not clipboardText.strip():
            QMessageBox.warning(
                self,
                "Clipboard Empty",
                "Clipboard is empty.",
            )
            return

        rows = self._parseClipboardTable(clipboardText)

        if not rows:
            QMessageBox.warning(
                self,
                "Invalid Clipboard Data",
                "No valid table data found in clipboard.",
            )
            return

        rows = self._normalizeClipboardRows(rows)

        self.tableWidget.setRowCount(len(rows))

        for rowIndex, rowValues in enumerate(rows):
            normalizedRow = self._normalizeTableRow(rowValues)

            for columnIndex, cellValue in enumerate(normalizedRow):
                item = QTableWidgetItem(cellValue)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tableWidget.setItem(rowIndex, columnIndex, item)

    def clearTable(self) -> None:
        self.tableWidget.setRowCount(0)

    def _parseClipboardTable(self, clipboardText: str) -> list[list[str]]:
        textStream = io.StringIO(clipboardText)

        if "\t" in clipboardText:
            reader = csv.reader(textStream, delimiter="\t")
        else:
            reader = csv.reader(textStream)

        rows = []

        for row in reader:
            if not row:
                continue

            if all(not cell.strip() for cell in row):
                continue

            rows.append([cell.strip() for cell in row])

        return rows

    def _normalizeClipboardRows(self, rows: list[list[str]]) -> list[list[str]]:
        if not rows:
            return rows

        headerMapping = self._getClipboardHeaderMapping(rows[0])

        if headerMapping is None:
            return rows

        normalizedRows = []

        for rowValues in rows[1:]:
            reorderedRow = []

            for header in self.TABLE_HEADERS:
                sourceIndex = headerMapping.get(header)

                if sourceIndex is None:
                    reorderedRow.append("")
                    continue

                if sourceIndex < len(rowValues):
                    reorderedRow.append(rowValues[sourceIndex])
                else:
                    reorderedRow.append("")

            normalizedRows.append(reorderedRow)

        return normalizedRows

    def _getClipboardHeaderMapping(
        self,
        firstRow: list[str],
    ) -> dict[str, int] | None:
        normalizedFirstRow = [
            self._normalizeHeaderText(cellValue)
            for cellValue in firstRow
        ]

        normalizedHeaderToIndex = {}

        for index, normalizedHeader in enumerate(normalizedFirstRow):
            if normalizedHeader:
                normalizedHeaderToIndex[normalizedHeader] = index

        requiredHeadersArePresent = all(
            self._normalizeHeaderText(header) in normalizedHeaderToIndex
            for header in self.REQUIRED_TABLE_HEADERS
        )

        if not requiredHeadersArePresent:
            return None

        allowedHeaders = {
            self._normalizeHeaderText(header)
            for header in self.TABLE_HEADERS
        }

        clipboardHeadersAreValid = all(
            normalizedHeader in allowedHeaders
            for normalizedHeader in normalizedFirstRow
            if normalizedHeader
        )

        if not clipboardHeadersAreValid:
            return None

        headerMapping = {}

        for expectedHeader in self.TABLE_HEADERS:
            normalizedExpectedHeader = self._normalizeHeaderText(expectedHeader)
            sourceIndex = normalizedHeaderToIndex.get(normalizedExpectedHeader)
            headerMapping[expectedHeader] = sourceIndex

        return headerMapping

    def _normalizeHeaderText(self, textValue: str) -> str:
        return " ".join(textValue.strip().lower().split())

    def _normalizeTableRow(self, rowValues: list[str]) -> list[str]:
        normalizedRow = ["", "", "", "", "", ""]

        for index in range(min(len(rowValues), len(normalizedRow))):
            normalizedRow[index] = rowValues[index]

        if not normalizedRow[self.COLUMN_WIDTH]:
            normalizedRow[self.COLUMN_WIDTH] = str(DEFAULT_WIDTH)

        if not normalizedRow[self.COLUMN_HEIGHT]:
            normalizedRow[self.COLUMN_HEIGHT] = str(DEFAULT_HEIGHT)

        if not normalizedRow[self.COLUMN_RESOLUTION]:
            normalizedRow[self.COLUMN_RESOLUTION] = str(DEFAULT_RESOLUTION)

        return normalizedRow

    def _getTableCellText(self, rowIndex: int, columnIndex: int) -> str:
        item = self.tableWidget.item(rowIndex, columnIndex)

        if item is None:
            return ""

        return item.text().strip()

    def _collectTasksFromTable(self) -> list[PsdTask]:
        tasks = []

        for rowIndex in range(self.tableWidget.rowCount()):
            fileName = self._getTableCellText(rowIndex, self.COLUMN_FILE_NAME)
            backgroundColor = self._getTableCellText(
                rowIndex,
                self.COLUMN_BACKGROUND_COLOR,
            )
            width = self._getTableCellText(rowIndex, self.COLUMN_WIDTH)
            height = self._getTableCellText(rowIndex, self.COLUMN_HEIGHT)
            resolution = self._getTableCellText(rowIndex, self.COLUMN_RESOLUTION)
            subDirectory = self._getTableCellText(
                rowIndex,
                self.COLUMN_SUB_DIRECTORY,
            )

            if not any(
                [
                    fileName,
                    backgroundColor,
                    width,
                    height,
                    resolution,
                    subDirectory,
                ]
            ):
                continue

            try:
                task = createTaskFromTableRow(
                    fileName=fileName,
                    backgroundColor=backgroundColor,
                    width=width,
                    height=height,
                    resolution=resolution,
                    subDirectory=subDirectory,
                )
            except Exception as error:
                raise ValueError(f"Table row {rowIndex + 1}: {error}") from error

            tasks.append(task)

        return tasks

    # ------------------------------------------------------------------
    # Text input
    # ------------------------------------------------------------------

    def _collectTasksFromText(self) -> list[PsdTask]:
        tasks = []
        lines = self.textInput.toPlainText().splitlines()

        for lineIndex, lineText in enumerate(lines, start=1):
            if not lineText.strip():
                continue

            try:
                task = createTaskFromTextLine(lineText)
            except Exception as error:
                raise ValueError(f"Text line {lineIndex}: {error}") from error

            tasks.append(task)

        return tasks

    # ------------------------------------------------------------------
    # Batch creation
    # ------------------------------------------------------------------

    def startBatchCreation(self) -> None:
        if self.workerThread is not None:
            QMessageBox.warning(
                self,
                "Batch Creation Running",
                "A batch creation process is already running.",
            )
            return

        try:
            tasks = self._collectTasksFromCurrentTab()
        except Exception as error:
            QMessageBox.critical(self, "Invalid Input", str(error))
            return

        if not tasks:
            QMessageBox.warning(
                self,
                "No Data",
                "There is no valid data to create PSD files.",
            )
            return

        outputDirectory = self.outputDirectoryLineEdit.text().strip()

        if not outputDirectory:
            QMessageBox.warning(
                self,
                "Missing Output Folder",
                "Please select an output folder.",
            )
            return

        self._saveSettings()
        self._startWorker(tasks, outputDirectory)

    def _startWorker(self, tasks: list[PsdTask], outputDirectory: str) -> None:
        self.progressWindow = ProgressWindow(self)
        self.progressWindow.setOutputDirectory(outputDirectory)
        self.progressWindow.setGeometry(self.geometry())
        self.progressWindow.show()

        self.workerThread = QThread()
        self.worker = PsdBatchWorker(tasks, outputDirectory)

        self.worker.moveToThread(self.workerThread)

        self.workerThread.started.connect(self.worker.run)

        self.worker.progressChanged.connect(self.progressWindow.updateProgress)
        self.worker.logMessage.connect(self.progressWindow.appendLog)
        self.worker.failed.connect(self.handleWorkerFailure)
        self.worker.finished.connect(self.handleWorkerFinished)

        self.progressWindow.cancelRequested.connect(
            self.worker.cancel,
            Qt.ConnectionType.DirectConnection,
        )

        self.progressWindow.openFolderRequested.connect(
            lambda: self.openOutputDirectory(Path(outputDirectory))
        )

        self.worker.finished.connect(self.workerThread.quit)
        self.worker.failed.connect(self.workerThread.quit)

        self.workerThread.finished.connect(self.worker.deleteLater)
        self.workerThread.finished.connect(self.workerThread.deleteLater)
        self.workerThread.finished.connect(self.clearWorkerReferences)

        self.workerThread.start()

    def _collectTasksFromCurrentTab(self) -> list[PsdTask]:
        currentIndex = self.tabWidget.currentIndex()

        if currentIndex == 0:
            return self._collectTasksFromTable()

        return self._collectTasksFromText()

    def handleWorkerFinished(self, wasCancelled: bool) -> None:
        if self.progressWindow is not None:
            self.progressWindow.markFinished(wasCancelled)

        if wasCancelled:
            QMessageBox.information(
                self.progressWindow,
                "Batch Creation Cancelled",
                "Batch creation was cancelled.",
            )
            return

        self.progressWindow.showSuccessMessage()

    def handleWorkerFailure(self, errorMessage: str) -> None:
        if self.progressWindow is not None:
            self.progressWindow.appendLog("An error occurred:")
            self.progressWindow.appendLog(errorMessage)
            self.progressWindow.markFinished(True)

        QMessageBox.critical(
            self.progressWindow,
            "Batch Creation Failed",
            "An error occurred while creating PSD files. "
            "See the progress window log for details.",
        )

    def clearWorkerReferences(self) -> None:
        self.workerThread = None
        self.worker = None

    def openOutputDirectory(self, outputDirectory: Path) -> None:
        outputDirectory.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(outputDirectory)))

    # ------------------------------------------------------------------
    # Output folder
    # ------------------------------------------------------------------

    def browseOutputDirectory(self) -> None:
        selectedDirectory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            self.outputDirectoryLineEdit.text().strip() or str(Path.cwd()),
        )

        if selectedDirectory:
            self.outputDirectoryLineEdit.setText(selectedDirectory)
            self._saveSettings()

    # ------------------------------------------------------------------
    # Window events
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        if self.worker is not None:
            QMessageBox.warning(
                self,
                "Batch Creation Running",
                "Please cancel or wait for the batch creation process to finish.",
            )
            event.ignore()
            return

        self._saveSettings()
        event.accept()