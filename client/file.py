import json
from config import LIST_PATH, FILE_PATH
# Saiid El Hajj Chehade

def readFile(fileName, fileType, directory):
    # get the full path to destination
    location = directory + "\\" + fileName + "." + fileType

    # write the binary data
    with open(location, 'rb') as f:
        data =f.read()

    return data

def writeFile(fileName, fileType, directory, data):
    """
    Writes the binary data to the given file location.

    :param fileName: str - name of file
    :param fileType: str - type of file
    :param directory: str - path to save in
    :param data: byteArray - binary data to save

    """

    # get the full path to destination
    location = directory + "\\" + fileName + "." + fileType

    # write the binary data
    with open(location, 'wb') as f:
        f.write(data)


# Saiid El Hajj Chehade
def segmentData(maxSize, data):
    """
    Segments the data array into a segment iterator

    :param maxSize: int - maximum number of bytes per segment
    :param data: byteArray - the data to segment

    :returns iterator - segment iterator.

    """

    segments = []

    # counter
    i = 0

    # append all the segments of length maxSize
    while i + maxSize < len(data):
        segments.append(data[i:i + maxSize])
        i += maxSize

    # append the last segment that is less than maxSize
    segments.append(data[i:])

    # return an iterator of the segments for better memory allocation
    return iter(segments), len(segments)


def compileData(dataSegments):
    return b''.join(dataSegments)

