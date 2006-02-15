__all__ = [
    'InMemoryConduit',
]

import Sharing
import logging

logger = logging.getLogger(__name__)

shareDict = { }

class InMemoryConduit(Sharing.ShareConduit):
    """ A test conduit, storing data in a dictionary """

    def __init__(self, *args, **kw):
        super(InMemoryConduit, self).__init__(*args, **kw)

        # self.shareDict = kw['shareDict'] # The dictionary to store shares into
        self.shareName = kw['shareName'] # The name of share within dictionary

    def getLocation(self):
        return self.shareName

    def exists(self):
        return shareDict.has_key(self.shareName)

    def create(self):
        super(InMemoryConduit, self).create()

        if self.exists():
            raise sharing.AlreadyExists(_(u"Share already exists"))

        style = self.share.format.fileStyle()
        if style == Sharing.ImportExportFormat.STYLE_DIRECTORY:
            shareDict[self.shareName] = { }
        # Nothing to do if style is SINGLE

    def destroy(self):
        super(InMemoryConduit, self).destroy()

        if not self.exists():
            raise NotFound(_(u"Share does not exist"))

        del shareDict[self.shareName]


    def _getResourceList(self, location):
        fileList = { }

        style = self.share.format.fileStyle()
        if style == Sharing.ImportExportFormat.STYLE_DIRECTORY:
            for (key, val) in shareDict[self.shareName].iteritems():
                fileList[key] = { 'data' : val[0] }

        return fileList

    def _putItem(self, item):
        path = self._getItemPath(item)

        try:
            text = self.share.format.exportProcess(item)
        except Exception, e:
            logging.exception(e)
            raise TransformationFailed(_(u"Transformation error: see chandler.log for more information"))

        if text is None:
            return None

        if shareDict[self.shareName].has_key(path):
            etag = shareDict[self.shareName][path][0]
            etag += 1
        else:
            etag = 0

        logger.debug("Putting text %s" % text)

        shareDict[self.shareName][path] = (etag, text)

        return etag

    def _getItem(self, itemPath, into=None, changes=None, previousView=None,
        updateCallback=None):

        view = self.itsView
        text = shareDict[self.shareName][itemPath][1]
        logger.debug("Getting text %s" % text)

        try:
            item = self.share.format.importProcess(text,
                item=into, changes=changes, previousView=previousView,
                updateCallback=updateCallback)
        except Exception, e:
            logging.exception(e)
            raise TransformationFailed(_(u"Transformation error: see chandler.log for more information"))

        return (item, shareDict[self.shareName][itemPath][0])


    def _deleteItem(self, itemPath):
        if shareDict[self.shareName].has_key(itemPath):
            del shareDict[self.shareName][itemPath]
