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

    addFile(fileName, fileType)


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


def getFileList():
    files = json.load(open(LIST_PATH, 'r'))
    output = []
    for file in files['files']:
        output.append({'file': file['name']+"."+file['type'], 'id': file['id']})
    return output

def addFile(fileName,fileType):
    files = json.load(open(LIST_PATH, 'r'))

    matches = [i for i in range(len(files['files'])) if files['files'][i]['name']==fileName and files['files'][i]['type']==fileType]
    if len(matches) >0: return

    files['lastFileID'] += 1
    files['files'].append({
        "id": files['lastFileID'],
        "name": fileName,
        "type": fileType
    })

    json.dump(files, open(LIST_PATH, 'w') )

def getFile(id, directory):
    files = json.load(open(LIST_PATH, 'r'))

    matches = [i for i in range(len(files['files'])) if files['files'][i]['id']==id]
    assert len(matches) > 0, "Couldn't find file with given id."

    return files['files'][matches[0]]['name'],files['files'][matches[0]]['type'], readFile(files['files'][matches[0]]['name'],files['files'][matches[0]]['type'], directory)