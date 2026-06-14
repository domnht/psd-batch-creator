from dataclasses import dataclass
from pathlib import Path
import re


DEFAULT_WIDTH = 4800
DEFAULT_HEIGHT = 4200
DEFAULT_RESOLUTION = 300

PSD_EXTENSION = ".psd"

HEX_COLOR_PATTERN = re.compile(r"#[0-9a-fA-F]{6}")

INVALID_FILE_NAME_CHARACTERS = r'<>:"/\|?*'
INVALID_DIRECTORY_NAME_CHARACTERS = r'<>:"|?*'


@dataclass
class PsdTask:
    fileName: str
    backgroundColor: str
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    resolution: int = DEFAULT_RESOLUTION
    subDirectory: str = ""

    def getOutputPath(self, outputDirectory: str | Path) -> Path:
        baseOutputPath = Path(outputDirectory)

        if self.subDirectory:
            baseOutputPath = baseOutputPath / self.subDirectory

        return baseOutputPath / ensurePsdExtension(sanitizeFileName(self.fileName))


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

    for character in INVALID_FILE_NAME_CHARACTERS:
        sanitizedName = sanitizedName.replace(character, "_")

    sanitizedName = sanitizedName.strip()

    if not sanitizedName:
        raise ValueError("File name cannot be empty after sanitizing.")

    return sanitizedName


def sanitizeSubDirectory(subDirectory: str) -> str:
    """
    Sanitize an optional relative subdirectory.

    Accepted examples:
        Part 1
        Part 1/Sub folder
        Part 1\\Sub folder

    Rejected:
        absolute paths
        paths containing ..
    """
    if subDirectory is None:
        return ""

    if not isinstance(subDirectory, str):
        raise TypeError("Sub directory must be a string.")

    normalizedSubDirectory = subDirectory.strip()

    if not normalizedSubDirectory:
        return ""

    normalizedSubDirectory = normalizedSubDirectory.replace("\\", "/")

    candidatePath = Path(normalizedSubDirectory)

    if candidatePath.is_absolute():
        raise ValueError("Sub directory must be a relative path.")

    rawParts = [
        part.strip()
        for part in normalizedSubDirectory.split("/")
        if part.strip()
    ]

    if not rawParts:
        return ""

    sanitizedParts = []

    for part in rawParts:
        if part in {".", ".."}:
            raise ValueError("Sub directory cannot contain '.' or '..'.")

        if ".." in part:
            raise ValueError("Sub directory cannot contain '..'.")

        sanitizedPart = part

        for character in INVALID_DIRECTORY_NAME_CHARACTERS:
            sanitizedPart = sanitizedPart.replace(character, "_")

        sanitizedPart = sanitizedPart.strip()

        if not sanitizedPart:
            raise ValueError("Sub directory contains an empty path segment.")

        sanitizedParts.append(sanitizedPart)

    return str(Path(*sanitizedParts))


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
    subDirectory: str = "",
) -> PsdTask:
    return PsdTask(
        fileName=sanitizeFileName(fileName),
        backgroundColor=normalizeHexColor(backgroundColor),
        width=parsePositiveInteger(width, "Width"),
        height=parsePositiveInteger(height, "Height"),
        resolution=parsePositiveInteger(resolution, "Resolution"),
        subDirectory=sanitizeSubDirectory(subDirectory),
    )


def createTaskFromTextLine(lineText: str) -> PsdTask:
    """
    Supported syntax:

    1. Create directly in the output folder:
        #010203 New document

    2. Create inside a subdirectory of the output folder:
        Part 1 #010203 New document
    """
    strippedLine = lineText.strip()

    if not strippedLine:
        raise ValueError("Line cannot be empty.")

    if strippedLine.startswith("#"):
        return _createTaskFromTextLineWithoutSubDirectory(strippedLine)

    return _createTaskFromTextLineWithSubDirectory(strippedLine)


def _createTaskFromTextLineWithoutSubDirectory(lineText: str) -> PsdTask:
    parts = lineText.split(maxsplit=1)

    if len(parts) < 2:
        raise ValueError(
            "Each line must contain a color and a document name. "
            "Example: #010203 New document"
        )

    backgroundColor = normalizeHexColor(parts[0])
    fileName = sanitizeFileName(parts[1])

    return PsdTask(
        fileName=fileName,
        backgroundColor=backgroundColor,
        width=DEFAULT_WIDTH,
        height=DEFAULT_HEIGHT,
        resolution=DEFAULT_RESOLUTION,
        subDirectory="",
    )


def _createTaskFromTextLineWithSubDirectory(lineText: str) -> PsdTask:
    colorMatch = HEX_COLOR_PATTERN.search(lineText)

    if colorMatch is None:
        raise ValueError(
            "A line with a sub directory must contain a hex color code. "
            "Example: Part 1 #010203 New document"
        )

    subDirectoryText = lineText[:colorMatch.start()].strip()
    backgroundColorText = colorMatch.group(0).strip()
    fileNameText = lineText[colorMatch.end():].strip()

    if not subDirectoryText:
        raise ValueError("Sub directory cannot be empty.")

    if not fileNameText:
        raise ValueError("File name cannot be empty.")

    return PsdTask(
        fileName=sanitizeFileName(fileNameText),
        backgroundColor=normalizeHexColor(backgroundColorText),
        width=DEFAULT_WIDTH,
        height=DEFAULT_HEIGHT,
        resolution=DEFAULT_RESOLUTION,
        subDirectory=sanitizeSubDirectory(subDirectoryText),
    )