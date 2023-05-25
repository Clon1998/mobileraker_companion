
from ctypes import cast
from datetime import datetime
from typing import Any, Dict


# "client": {
#     "lastSeen": "2023-05-15T20:19:33.631285",
#     "version": "v0.3.0-3-g00502b8"
# },

class CompanionMetaDataDto:
    def __init__(self,
                 last_seen: datetime = datetime.now(),
                 version: str = ''
                 ):
        self.last_seen: datetime = last_seen
        self.version: str = version

    @staticmethod
    def fromJSON(json: Dict[str, Any]) -> 'CompanionMetaDataDto':
        metaData = CompanionMetaDataDto()

        metaData.last_seen = json['lastSeen'] if 'lastSeen' in json else datetime.now(
        )
        metaData.version = json['version'] if 'version' in json else ''

        return metaData

    def toJSON(self) -> Dict[str, Any]:
        return {
            "lastSeen": self.last_seen.isoformat(),
            "version": self.version,
        }

    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )
