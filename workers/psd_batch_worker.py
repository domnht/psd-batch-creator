from pathlib import Path
import traceback

from PyQt6.QtCore import QObject, pyqtSignal

from utils.photoshop_document import PhotoshopDocument
from utils.psd_task import PsdTask


class PsdBatchWorker(QObject):
    progressChanged = pyqtSignal(int, int)
    logMessage = pyqtSignal(str)
    finished = pyqtSignal(bool)
    failed = pyqtSignal(str)

    def __init__(self, tasks: list[PsdTask], outputDirectory: str | Path):
        super().__init__()

        self.tasks = tasks
        self.outputDirectory = Path(outputDirectory)
        self.isCancelled = False

    def cancel(self) -> None:
        self.isCancelled = True
        self.logMessage.emit("Cancel signal received.")

    def run(self) -> None:
        try:
            self.outputDirectory.mkdir(parents=True, exist_ok=True)

            totalTasks = len(self.tasks)

            if totalTasks == 0:
                self.logMessage.emit("No PSD files to create.")
                self.progressChanged.emit(0, 0)
                self.finished.emit(False)
                return

            self.logMessage.emit(f"Output directory: {self.outputDirectory}")
            self.logMessage.emit(f"Total files: {totalTasks}\n")

            completedTasks = 0

            for taskIndex, task in enumerate(self.tasks, start=1):
                if self.isCancelled:
                    self.logMessage.emit("Batch creation was cancelled.")
                    self.finished.emit(True)
                    return

                outputPath = task.getOutputPath(self.outputDirectory)
                outputPath.parent.mkdir(parents=True, exist_ok=True)

                if task.subDirectory:
                    self.logMessage.emit(
                        f"[{taskIndex}/{totalTasks}] Creating: "
                        f"{task.subDirectory}/{outputPath.name}"
                    )
                else:
                    self.logMessage.emit(
                        f"[{taskIndex}/{totalTasks}] Creating: {outputPath.name}"
                    )

                photoshopDocument = PhotoshopDocument(
                    width=task.width,
                    height=task.height,
                    resolution=task.resolution,
                    backgroundColor=task.backgroundColor,
                    layerName="Background",
                )

                photoshopDocument.createPsdFile(outputPath)

                completedTasks += 1

                fileSize = outputPath.stat().st_size

                if task.subDirectory:
                    displayPath = f"{task.subDirectory}/{outputPath.name}"
                else:
                    displayPath = outputPath.name

                self.logMessage.emit(
                    f"Done: {displayPath} | "
                    f"{task.width}x{task.height} | "
                    f"{task.resolution} ppi | "
                    f"{task.backgroundColor} | "
                    f"{fileSize:,} bytes\n"
                )

                self.progressChanged.emit(completedTasks, totalTasks)

            self.logMessage.emit("Finished.")
            self.finished.emit(False)

        except Exception:
            self.failed.emit(traceback.format_exc())