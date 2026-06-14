from dataclasses import dataclass
from pathlib import Path
import re


DEFAULT_WIDTH = 4200
DEFAULT_HEIGHT = 4800
DEFAULT_RESOLUTION = 300

PSD_EXTENSION = ".psd"


@dataclass
class PsdTask:
    fileName: str
    backgroundColor: str
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    resolution: int = DEFAULT_RESOLUTION

    def getOutputPath(self, outputDirectory: str | Path) -> Path:
        outputPath = Path(outputDirectory)
        return outputPath / ensurePsdExtension(sanitizeFileName(self.fileName))


def normalizeHexColor(colorValue: str) -> str:
    if not isinstance(colorValue, str):
        raise TypeError("Color value must be a string.")

    normalizedColor = colorValue.strip()

    if not normalizedColor:
        raise ValueError("Color value cannot be empty.")

    if not normalizedColor.startswith("#"):
        normalizedColor = "#" + normalizedColor

    if not re.fullmatch(r"#[0-9a-fA-F]{6}", normalizedColor):
        raise ValueError(f"Invalid hex color: {colorValue}")

    return normalizedColor.upper()


def sanitizeFileName(fileName: str) -> str:
    if not isinstance(fileName, str):
        raise TypeError("File name must be a string.")

    sanitizedName = fileName.strip()

    if not sanitizedName:
        raise ValueError("File name cannot be empty.")

    invalidCharacters = r'<>:"|?*'

    for character in invalidCharacters:
        sanitizedName = sanitizedName.replace(character, "_")

    sanitizedName = sanitizedName.strip()

    if not sanitizedName:
        raise ValueError("File name cannot be empty after sanitizing.")

    return sanitizedName


def ensurePsdExtension(fileName: str) -> str:
    if not fileName.lower().endswith(PSD_EXTENSION):
        return fileName + PSD_EXTENSION

    return fileName


def parsePositiveInteger(value: str | int, fieldName: str) -> int:
    if isinstance(value, int):
        integerValue = value
    else:
        textValue = str(value).strip()

        if not textValue:
            raise ValueError(f"{fieldName} cannot be empty.")

        integerValue = int(textValue)

    if integerValue <= 0:
        raise ValueError(f"{fieldName} must be greater than 0.")

    return integerValue


def createTaskFromTableRow(
    fileName: str,
    backgroundColor: str,
    width: str,
    height: str,
    resolution: str,
) -> PsdTask:
    return PsdTask(
        fileName=sanitizeFileName(fileName),
        backgroundColor=normalizeHexColor(backgroundColor),
        width=parsePositiveInteger(width, "Width"),
        height=parsePositiveInteger(height, "Height"),
        resolution=parsePositiveInteger(resolution, "Resolution"),
    )


def createTaskFromTextLine(lineText: str) -> PsdTask:
    strippedLine = lineText.strip()

    if not strippedLine:
        raise ValueError("Line cannot be empty.")

    parts = strippedLine.split(maxsplit=1)

    if len(parts) < 2:
        raise ValueError(
            "Each line must contain a color and a document name. "
            "Example: #000000 Document 1"
        )

    backgroundColor = normalizeHexColor(parts[0])
    fileName = sanitizeFileName(parts[1])

    return PsdTask(
        fileName=fileName,
        backgroundColor=backgroundColor,
        width=DEFAULT_WIDTH,
        height=DEFAULT_HEIGHT,
        resolution=DEFAULT_RESOLUTION,
    )
