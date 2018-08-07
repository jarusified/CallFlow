import json
from logger import log
import os

class configFileReader():
    def __init__(self, filepath):
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, filepath)
        print(filename)
        f = open(filename, 'r')
        self.data = self.json_data(f.read())
        log.info('Config file: {0}'.format(self.data))
        print(self.data)
        self.paths = self.data['path']
        self.props = self.data['props']
        self.format = self.data['format'] if 'format' in self.data.keys() else None
        self.fnMap = self.getFuncMap()
        self.fileMap = self.getFileMap()
        
    # File map from the config file
    def getFileMap(self):
        fileMap = {}
        for obj in self.props:
            name = self.props[obj]['name']
            fileMap[name] = self.props[obj]['files']
        return fileMap

    # Function map from the config file
    def getFuncMap(self):
        funcMap = {}
        for obj in self.props:            
            name = self.props[obj]['name']
            funcMap[name] = self.props[obj]['functions']
        return funcMap

    def json_data(self, json_text):
        return self._byteify(json.loads(json_text, object_hook=self._byteify), ignore_dicts=True)
    
    def _byteify(self, data, ignore_dicts = False):
        # if this is a unicode string, return its string representation
        if isinstance(data, bytes):
            return data.encode('utf-8')
        # if this is a list of values, return list of byteified values
        if isinstance(data, list):
            return [ self._byteify(item, ignore_dicts=True) for item in data ]
        # if this is a dictionary, return dictionary of byteified keys and values
        # but only if we haven't already byteified it
        if isinstance(data, dict) and not ignore_dicts:
            return {
                self._byteify(key, ignore_dicts=True): self._byteify(value, ignore_dicts=True) for key, value in data.items()
            }
        # if it's anything else, return it in its original form
        return data


class configFileWriter():
    def __init__():
        return 0