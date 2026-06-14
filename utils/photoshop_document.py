from pathlib import Path
import struct
import time

class PhotoshopDocument:
    """
    Minimal PSD writer for creating a flat-color RGB/8 Photoshop document
    with one named layer.

    Supported features:
    - PSD version 1
    - RGB/8 color mode
    - RLE PackBits compression
    - One visible layer
    - Resolution metadata in pixels per inch
    """

    PSD_SIGNATURE = b"8BPS"
    PSD_VERSION = 1

    COLOR_MODE_RGB = 3
    DEPTH_8_BIT = 8
    CHANNEL_COUNT_RGB = 3

    COMPRESSION_RLE = 1

    IMAGE_RESOURCE_SIGNATURE = b"8BIM"
    IMAGE_RESOURCE_ID_RESOLUTION_INFO = 1005

    BLEND_MODE_SIGNATURE = b"8BIM"
    BLEND_MODE_NORMAL = b"norm"

    CHANNEL_ID_RED = 0
    CHANNEL_ID_GREEN = 1
    CHANNEL_ID_BLUE = 2

    DEFAULT_RESOLUTION = 300
    DEFAULT_BACKGROUND_COLOR = "#010000"
    DEFAULT_LAYER_NAME = "Background"

    def __init__(
        self,
        width: int,
        height: int,
        resolution: int = DEFAULT_RESOLUTION,
        backgroundColor: str = DEFAULT_BACKGROUND_COLOR,
        layerName: str = DEFAULT_LAYER_NAME,
    ):
        self._width = self._validatePositiveInteger(width, "width")
        self._height = self._validatePositiveInteger(height, "height")
        self._resolution = self._validatePositiveInteger(resolution, "resolution")
        self._backgroundColor = self._parseHexColor(backgroundColor)
        self._layerName = self._validateLayerName(layerName)

    # ------------------------------------------------------------------
    # Public creation method
    # ------------------------------------------------------------------

    def createPsdFile(self, outputFile: str | Path) -> Path:
        """
        Create a PSD file using the current document properties.

        Example:
            document = PhotoshopDocument(
                width=4200,
                height=4800,
                resolution=300,
                backgroundColor="#010000",
                layerName="Background"
            )

            document.createPsdFile("Demo Ps Document.psd")
        """
        outputPath = Path(outputFile)

        redValue, greenValue, blueValue = self._backgroundColor

        layerChannels = [
            self._buildRleChannelData(redValue),
            self._buildRleChannelData(greenValue),
            self._buildRleChannelData(blueValue),
        ]

        psdData = bytearray()

        psdData += self._buildFileHeaderSection()
        psdData += self._buildColorModeDataSection()
        psdData += self._buildImageResourcesSection()
        psdData += self._buildLayerAndMaskSection(layerChannels)
        psdData += self._buildCompositeImageDataSection(
            [redValue, greenValue, blueValue]
        )

        outputPath.write_bytes(psdData)
        time.sleep(1)
        return outputPath

    # ------------------------------------------------------------------
    # Getter methods
    # ------------------------------------------------------------------

    def getWidth(self) -> int:
        return self._width

    def getHeight(self) -> int:
        return self._height

    def getResolution(self) -> int:
        return self._resolution

    def getBackgroundColor(self) -> str:
        redValue, greenValue, blueValue = self._backgroundColor
        return f"#{redValue:02X}{greenValue:02X}{blueValue:02X}"

    def getBackgroundColorRgb(self) -> tuple[int, int, int]:
        return self._backgroundColor

    def getLayerName(self) -> str:
        return self._layerName

    # ------------------------------------------------------------------
    # Setter methods
    # ------------------------------------------------------------------

    def setWidth(self, width: int) -> None:
        self._width = self._validatePositiveInteger(width, "width")

    def setHeight(self, height: int) -> None:
        self._height = self._validatePositiveInteger(height, "height")

    def setResolution(self, resolution: int) -> None:
        self._resolution = self._validatePositiveInteger(resolution, "resolution")

    def setBackgroundColor(self, backgroundColor: str) -> None:
        self._backgroundColor = self._parseHexColor(backgroundColor)

    def setBackgroundColorRgb(
        self,
        redValue: int,
        greenValue: int,
        blueValue: int,
    ) -> None:
        self._backgroundColor = (
            self._validateByte(redValue, "redValue"),
            self._validateByte(greenValue, "greenValue"),
            self._validateByte(blueValue, "blueValue"),
        )

    def setLayerName(self, layerName: str) -> None:
        self._layerName = self._validateLayerName(layerName)

    # ------------------------------------------------------------------
    # PSD section builders
    # ------------------------------------------------------------------

    def _buildFileHeaderSection(self) -> bytes:
        """
        Build the PSD File Header Section.
        """
        sectionData = bytearray()

        sectionData += self.PSD_SIGNATURE
        sectionData += self._packUnsignedShort(self.PSD_VERSION)
        sectionData += b"\x00" * 6
        sectionData += self._packUnsignedShort(self.CHANNEL_COUNT_RGB)
        sectionData += self._packUnsignedInteger(self._height)
        sectionData += self._packUnsignedInteger(self._width)
        sectionData += self._packUnsignedShort(self.DEPTH_8_BIT)
        sectionData += self._packUnsignedShort(self.COLOR_MODE_RGB)

        return bytes(sectionData)

    def _buildColorModeDataSection(self) -> bytes:
        """
        Build the Color Mode Data Section.

        For RGB documents, this section is empty.
        """
        return self._packUnsignedInteger(0)

    def _buildImageResourcesSection(self) -> bytes:
        """
        Build the Image Resources Section.

        This section includes the ResolutionInfo resource.
        """
        resourcesData = bytearray()

        resourcesData += self._buildImageResourceBlock(
            resourceId=self.IMAGE_RESOURCE_ID_RESOLUTION_INFO,
            resourceData=self._buildResolutionInfoResource(),
            resourceName="",
        )

        return self._packUnsignedInteger(len(resourcesData)) + resourcesData

    def _buildLayerAndMaskSection(self, layerChannels: list[bytes]) -> bytes:
        """
        Build the Layer and Mask Information Section.
        """
        layerRecord = self._buildLayerRecord(
            channelLengths=[len(channelData) for channelData in layerChannels],
            layerName=self._layerName,
        )

        layerInfoData = bytearray()

        layerInfoData += self._packSignedShort(1)
        layerInfoData += layerRecord

        for channelData in layerChannels:
            layerInfoData += channelData

        layerAndMaskData = bytearray()

        layerAndMaskData += self._packUnsignedInteger(len(layerInfoData))
        layerAndMaskData += layerInfoData

        layerAndMaskData += self._packUnsignedInteger(0)

        return self._packUnsignedInteger(len(layerAndMaskData)) + layerAndMaskData

    def _buildCompositeImageDataSection(self, rgbValues: list[int]) -> bytes:
        """
        Build the final composite image data section.

        Photoshop expects composite image data even if the document has layers.
        """
        sectionData = bytearray()

        sectionData += self._packUnsignedShort(self.COMPRESSION_RLE)

        encodedRows = [
            self._packBitsRow(channelValue)
            for channelValue in rgbValues
        ]

        for encodedRow in encodedRows:
            rowLength = len(encodedRow)

            for _ in range(self._height):
                sectionData += self._packUnsignedShort(rowLength)

        for encodedRow in encodedRows:
            for _ in range(self._height):
                sectionData += encodedRow

        return bytes(sectionData)

    # ------------------------------------------------------------------
    # PSD layer helpers
    # ------------------------------------------------------------------

    def _buildLayerRecord(self, channelLengths: list[int], layerName: str) -> bytes:
        """
        Build a single PSD layer record.
        """
        recordData = bytearray()

        recordData += self._packSignedInteger(0)
        recordData += self._packSignedInteger(0)
        recordData += self._packSignedInteger(self._height)
        recordData += self._packSignedInteger(self._width)

        recordData += self._packUnsignedShort(self.CHANNEL_COUNT_RGB)

        channelIds = [
            self.CHANNEL_ID_RED,
            self.CHANNEL_ID_GREEN,
            self.CHANNEL_ID_BLUE,
        ]

        for channelId, channelLength in zip(channelIds, channelLengths):
            recordData += self._packSignedShort(channelId)
            recordData += self._packUnsignedInteger(channelLength)

        recordData += self.BLEND_MODE_SIGNATURE
        recordData += self.BLEND_MODE_NORMAL

        recordData += bytes([255])
        recordData += bytes([0])
        recordData += bytes([0])
        recordData += bytes([0])

        extraData = bytearray()

        extraData += self._packUnsignedInteger(0)
        extraData += self._packUnsignedInteger(0)
        extraData += self._buildPascalStringPaddedToFourBytes(layerName)

        recordData += self._packUnsignedInteger(len(extraData))
        recordData += extraData

        return bytes(recordData)

    # ------------------------------------------------------------------
    # Compression helpers
    # ------------------------------------------------------------------

    def _buildRleChannelData(self, channelValue: int) -> bytes:
        """
        Build RLE-compressed image data for one full channel.

        Format:
        - 2 bytes: compression method
        - 2 bytes per row: compressed byte count
        - compressed row data
        """
        encodedRow = self._packBitsRow(channelValue)
        rowLength = len(encodedRow)

        channelData = bytearray()

        channelData += self._packUnsignedShort(self.COMPRESSION_RLE)

        for _ in range(self._height):
            channelData += self._packUnsignedShort(rowLength)

        for _ in range(self._height):
            channelData += encodedRow

        return bytes(channelData)

    def _packBitsRow(self, channelValue: int) -> bytes:
        """
        Encode one row of identical bytes using PackBits RLE.

        A repeated run of N bytes is encoded as:
            control byte = 257 - N
            repeated byte = channelValue

        The maximum PackBits run length is 128 bytes.
        """
        rowData = bytearray()
        remainingPixels = self._width

        while remainingPixels > 0:
            runLength = min(128, remainingPixels)

            rowData.append(257 - runLength)
            rowData.append(channelValue)

            remainingPixels -= runLength

        return bytes(rowData)

    # ------------------------------------------------------------------
    # Image resource helpers
    # ------------------------------------------------------------------

    def _buildImageResourceBlock(self, resourceId: int, resourceData: bytes, resourceName: str = "") -> bytes:
        """
        Build one Photoshop Image Resource block.
        """
        blockData = bytearray()

        blockData += self.IMAGE_RESOURCE_SIGNATURE
        blockData += self._packUnsignedShort(resourceId)
        blockData += self._buildPascalStringPaddedToTwoBytes(resourceName)
        blockData += self._packUnsignedInteger(len(resourceData))
        blockData += resourceData

        if len(resourceData) % 2 != 0:
            blockData += b"\x00"

        return bytes(blockData)

    def _buildResolutionInfoResource(self) -> bytes:
        """
        Build Photoshop ResolutionInfo resource data.

        ResolutionInfo uses a 32-bit fixed-point value.
        """
        fixedResolution = self._resolution << 16

        resourceData = bytearray()

        resourceData += self._packUnsignedInteger(fixedResolution)
        resourceData += self._packUnsignedShort(1)
        resourceData += self._packUnsignedShort(1)

        resourceData += self._packUnsignedInteger(fixedResolution)
        resourceData += self._packUnsignedShort(1)
        resourceData += self._packUnsignedShort(1)

        return bytes(resourceData)

    # ------------------------------------------------------------------
    # String encoding helpers
    # ------------------------------------------------------------------

    def _buildPascalStringPaddedToTwoBytes(self, text: str) -> bytes:
        """
        Build a Pascal string padded to an even byte length.
        """
        rawText = text.encode("macroman", errors="replace")[:255]

        stringData = bytes([len(rawText)]) + rawText

        if len(stringData) % 2 != 0:
            stringData += b"\x00"

        return stringData

    def _buildPascalStringPaddedToFourBytes(self, text: str) -> bytes:
        """
        Build a Pascal string padded to a multiple of four bytes.
        """
        rawText = text.encode("macroman", errors="replace")[:255]

        stringData = bytes([len(rawText)]) + rawText

        while len(stringData) % 4 != 0:
            stringData += b"\x00"

        return stringData

    # ------------------------------------------------------------------
    # Binary packing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _packUnsignedShort(value: int) -> bytes:
        return struct.pack(">H", value)

    @staticmethod
    def _packSignedShort(value: int) -> bytes:
        return struct.pack(">h", value)

    @staticmethod
    def _packUnsignedInteger(value: int) -> bytes:
        return struct.pack(">I", value)

    @staticmethod
    def _packSignedInteger(value: int) -> bytes:
        return struct.pack(">i", value)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validatePositiveInteger(value: int, valueName: str) -> int:
        if not isinstance(value, int):
            raise TypeError(f"{valueName} must be an integer.")

        if value <= 0:
            raise ValueError(f"{valueName} must be greater than 0.")

        return value

    @staticmethod
    def _validateByte(value: int, valueName: str) -> int:
        if not isinstance(value, int):
            raise TypeError(f"{valueName} must be an integer.")

        if value < 0 or value > 255:
            raise ValueError(f"{valueName} must be between 0 and 255.")

        return value

    @staticmethod
    def _validateLayerName(layerName: str) -> str:
        if not isinstance(layerName, str):
            raise TypeError("layerName must be a string.")

        if layerName == "":
            raise ValueError("layerName cannot be empty.")

        encodedLayerName = layerName.encode("macroman", errors="replace")

        if len(encodedLayerName) > 255:
            raise ValueError("layerName cannot exceed 255 bytes.")

        return layerName

    @staticmethod
    def _parseHexColor(colorValue: str) -> tuple[int, int, int]:
        """
        Parse an RGB hex color.

        Accepted formats:
            #RRGGBB
            RRGGBB
        """
        if not isinstance(colorValue, str):
            raise TypeError("backgroundColor must be a string.")

        normalizedColor = colorValue.strip()

        if normalizedColor.startswith("#"):
            normalizedColor = normalizedColor[1:]

        if len(normalizedColor) != 6:
            raise ValueError("backgroundColor must use the #RRGGBB format.")

        try:
            redValue = int(normalizedColor[0:2], 16)
            greenValue = int(normalizedColor[2:4], 16)
            blueValue = int(normalizedColor[4:6], 16)
        except ValueError as error:
            raise ValueError(
                "backgroundColor contains invalid hexadecimal digits."
            ) from error

        return redValue, greenValue, blueValue
