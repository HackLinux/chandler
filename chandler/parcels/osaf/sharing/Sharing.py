__version__ = "$Revision$"
__date__ = "$Date$"
__copyright__ = "Copyright (c) 2004 Open Source Applications Foundation"
__license__ = "http://osafoundation.org/Chandler_0.1_license_terms.htm"


import time, urlparse, libxml2, os, base64, logging

from application import schema
from osaf import pim, messages, ChandlerException
import application.dialogs.AccountInfoPrompt as AccountInfoPrompt
from i18n import OSAFMessageFactory as _
import osaf.mail.utils as utils

from chandlerdb.util.c import UUID
from repository.item.Item import Item
from repository.item.Sets import Set
from repository.schema.Types import Type
from repository.util.Lob import Lob

import M2Crypto.BIO, WebDAV, twisted.web.http, zanshin.webdav, wx

logger = logging.getLogger(__name__)

__all__ = [
    'AlreadyExists',
    'AlreadySubscribed',
    'CalDAVConduit',
    'CloudXMLFormat',
    'CouldNotConnect',
    'FileSystemConduit',
    'IllegalOperation',
    'ImportExportFormat',
    'Misconfigured',
    'NotAllowed',
    'NotFound',
    'OneTimeFileSystemShare',
    'OneTimeShare',
    'Share',
    'ShareConduit',
    'SharingError',
    'SimpleHTTPConduit',
    'TransformationFailed',
    'WebDAVAccount',
    'WebDAVConduit',
    'changedAttributes',
    'importValue',
    'isShared',
    'splitUrl',
    'sync',
]

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

CLOUD_XML_VERSION = '2'

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

USE_VIEW_MERGING = False


def sync(collectionOrShares, modeOverride=None, updateCallback=None):

    view_merging = USE_VIEW_MERGING # May be enabled via Test menu

    def mergeFunction(code, item, attribute, value):

        logger.debug("Conflict during sync on item %(item)s, attribute "
            "%(attribute)s" % {
                'item' : item,
                'attribute' : attribute,
            })

        LOCAL_CHANGES_WIN = False
        if LOCAL_CHANGES_WIN:
            return value
        else:
            return item.getAttributeValue(attribute)


    if isinstance(collectionOrShares, list):
        # a list of Shares
        shares = collectionOrShares
        view = shares[0].itsView
        marker = shares[0].conduit.marker

    elif isinstance(collectionOrShares, Share):
        # just one Share
        shares = [collectionOrShares]
        view = collectionOrShares.itsView
        marker = collectionOrShares.conduit.marker

    else:
        # just a collection
        if not isShared(collectionOrShares):
            return
        shares = getLinkedShares(collectionOrShares.shares.first())
        view = collectionOrShares.itsView
        marker = shares[0].conduit.marker

    # Make main view changes available for sharing
    if updateCallback:
        updateCallback(msg=_(u"Saving changes..."))
    view.commit()

    stats = []

    # previousView will be used by importValue() to look back in time to see
    # if changes we've received from the server are really new or whether they
    # are attributes along for the ride when importing a modified resource.
    previousView = None

    if view_merging:

        if updateCallback:
            updateCallback(msg=_(u"Using view merging"))

        syncVersion = marker.getVersion()

        sharingView = None
        for existingView in view.repository.views:
            if existingView.name == 'Sharing':
                sharingView = existingView

        if sharingView is None:
            sharingView = view.repository.createView("Sharing", syncVersion)
        else:
            sharingView.itsVersion = syncVersion

        workingShares = []
        for share in shares:
            workingShares.append(sharingView.findUUID(share.itsUUID))

    else:
        # Not using view merging, but we have another form of merging, via
        # the importValue( ) method.

        sharingView = view
        workingShares = shares

        syncVersion = marker.getVersion()

        # Here we get a view as things were the last time we synced, so that
        # importValue( ) can determine whether imported changes are real;
        # We either create a new view or use our existing one, and set its
        # version back in time.

        for existingView in view.repository.views:
            if existingView.name == 'Sharing':
                previousView = existingView

        if previousView is None:
            previousView = view.repository.createView("Sharing", syncVersion)
        else:
            previousView.itsVersion = syncVersion


    try:

        if not modeOverride or modeOverride == 'get':

            # perform the 'get' operations of all associated shares, applying
            # remote changes locally
            contents = None
            filterClasses = None
            for share in workingShares:
                if share.active and share.mode in ('get', 'both'):
                    if contents:
                        # If there are multiple shares involved, we take the
                        # resulting contents from the first Share and hand that
                        # to the remaining Shares:
                        share.contents = contents
                    if filterClasses is not None:
                        # like 'contents' above, the filterClasses of a master
                        # share needs to be replicated to the slaves:
                        share.filterClasses = filterClasses

                    stat = share.conduit._get(previousView=previousView,
                        updateCallback=updateCallback)
                    stats.append(stat)
                    contents = share.contents
                    filterClasses = share.filterClasses

            # Bug 4564 -- half baked calendar events (those with .xml resources
            # but not .ics resources)
            #
            # We need to detect/delete them from the repository.  This means
            # looking through the stats to find the items we just got, seeing
            # which ones are CalendarEventMixin, and removing any that don't
            # have a startTime.  Next, we need to adjust the manifests so that
            # during the PUT phase we don't remove the .xml resources from
            # the server
            #
            halfBakedEvents = []
            for stat in stats:
                share = sharingView.findUUID(stat['share'])
                for uuid in stat['added']:
                    item = sharingView.findUUID(uuid)
                    if isinstance(item, pim.CalendarEventMixin):
                        if not hasattr(item, 'startTime'):
                            if updateCallback:
                                updateCallback(msg=_(u"Incomplete Event Detected: '%(name)s'") % { 'name': item.getItemDisplayName() } )

                            # This indicates the resource is to be ignored
                            # during PUT (otherwise we would remove the .xml
                            # resource since the item isn't in our local copy
                            # of the collection:
                            itemPath = share.conduit._getItemPath(item)
                            share.conduit._addToManifest(itemPath, None)

                            # There is another bug we're working around,
                            # bug 4578, which requires I move the event to
                            # the trash before deleting it:
                            if hasattr(share.contents, 'trash'):
                                share.contents.trash.add(item)

                            item.delete(True)

        if view_merging:
            # Pull in local changes from main view
            if updateCallback:
                updateCallback(msg=_(u"Merging local changes..."))
            sharingView.refresh(mergeFunction)

        if not modeOverride or modeOverride == 'put':

            # perform the 'put' operations of all associated shares, putting
            # local changes to server
            for share in workingShares:
                if share.active and share.mode in ('put', 'both'):
                    stat = share.conduit._put(updateCallback=updateCallback)
                    stats.append(stat)

        for share in workingShares:
            share.conduit.marker.setDirty(Item.NDIRTY)

        if updateCallback:
            updateCallback(msg=_(u"Saving changes..."))

        if view_merging:
            # Make remote changes available to main view
            sharingView.commit()
            # Pull remote changes into main view
            view.refresh()
        else:
            # Demarcate the end of sync (bumps up the marker version)
            view.commit()

    except Exception, e:
        logger.exception("Sharing Error: %s" % e)

        sharingView.cancel()

        if view_merging:
            sharingView.clear()

        for share in shares:
            if hasattr(e, 'message'): # Sharing Error
                share.error = e.message
            else:
                share.error = str(e)
        raise

    for share in shares:
        if hasattr(share, 'error'):
            del share.error

    return stats

def getLinkedShares(share):

    def getFollowers(share):
        if hasattr(share, 'leads'):
            for follower in share.leads:
                yield follower
                for subfollower in getFollowers(follower):
                    yield subfollower

    # Find the root leader
    root = share
    leader = getattr(root, 'follows', None)
    while leader is not None:
        root = leader
        leader = getattr(root, 'follows', None)

    shares = [root]
    for follower in getFollowers(root):
        shares.append(follower)

    return shares


class modeEnum(schema.Enumeration):
    schema.kindInfo(displayName=u"Mode Enumeration")
    values = "put", "get", "both"


class Share(pim.ContentItem):
    """
    Represents a set of shared items, encapsulating contents, location,
    access method, data format, sharer and sharees.
    """

    schema.kindInfo(
        displayName=u"Share Kind",
        description="Represents a shared collection",
    )

    hidden = schema.One(
        schema.Boolean,
        doc = 'This attribute is used to denote which shares have been '
              'created by the user via the detail view (hidden=False) versus '
              'those that are being created for other purposes (hidden=True), '
              'such as transient import/export shares, .ics publishing, etc.',
        initialValue = False,
    )

    active = schema.One(
        schema.Boolean,
        doc = "This attribute indicates whether this share should be synced "
              "during a 'sync all' operation.",
        initialValue = True,
    )

    mode = schema.One(
        modeEnum,
        doc = 'This attribute indicates the sync mode for the share:  '
              'get, put, or both',
        initialValue = 'both',
    )

    error = schema.One(
        schema.Text,
        doc = 'A message describing the last error; empty string otherwise',
        initialValue = u''
    )

    contents = schema.One(pim.ContentItem,otherName='shares',initialValue=None)

    items = schema.Sequence(pim.ContentItem, initialValue=[],
        otherName = 'sharedIn')

    conduit = schema.One('ShareConduit', inverse='share', initialValue=None)

    format = schema.One('ImportExportFormat',inverse='share',initialValue=None)

    sharer = schema.One(
        pim.Contact,
        doc = 'The contact who initially published this share',
        initialValue = None,
        otherName = 'sharerOf',
    )

    sharees = schema.Sequence(
        pim.Contact,
        doc = 'The people who were invited to this share',
        initialValue = [],
        otherName = 'shareeOf',
    )

    filterClasses = schema.Sequence(
        schema.Text,
        doc = 'The list of classes to import/export',
        initialValue = [],
    )

    filterAttributes = schema.Sequence(schema.Text, initialValue=[])

    leads = schema.Sequence('Share', initialValue=[], otherName='follows')
    follows = schema.One('Share', otherName='leads')

    schema.addClouds(
        sharing = schema.Cloud(byCloud=[contents,sharer,sharees,filterClasses,
                                        filterAttributes]),
        copying = schema.Cloud(byCloud=[format, conduit])
    )

    def __init__(self, *args, **kw):
        defaultDisplayName = getattr(kw.get('contents'),'displayName',u'')
        kw.setdefault('displayName',defaultDisplayName)
        super(Share, self).__init__(*args, **kw)

    def create(self):
        self.conduit.create()

    def destroy(self):
        self.conduit.destroy()

    def open(self):
        self.conduit.open()

    def close(self):
        self.conduit.close()

    def sync(self, modeOverride=None, updateCallback=None):
        return sync(getLinkedShares(self), modeOverride=modeOverride,
            updateCallback=updateCallback)

    def put(self, updateCallback=None):
        return sync(getLinkedShares(self), modeOverride='put',
             updateCallback=updateCallback)

    def get(self, updateCallback=None):
        return sync(getLinkedShares(self), modeOverride='get',
             updateCallback=updateCallback)

    def exists(self):
        return self.conduit.exists()

    def getLocation(self, privilege=None):
        return self.conduit.getLocation(privilege=privilege)

    def getCount(self):
        return self.conduit.getCount()

    def getSharedAttributes(self, item, cloudAlias='sharing'):
        """
        Examine sharing clouds and filterAttributes to determine which
        attributes to share for a given item
        """

        attributes = []
        skip = {}
        if hasattr(self, 'filterAttributes'):
            for attrName in self.filterAttributes:
                skip[attrName] = 1

        for cloud in item.itsKind.getClouds(cloudAlias):
            for (alias, endpoint, inCloud) in cloud.iterEndpoints(cloudAlias):
                # @@@MOR for now, don't support endpoint attribute 'chains'
                attrName = endpoint.attribute[0]

                # An includePolicy of 'none' is how we override an inherited
                # endpoint
                if endpoint.includePolicy == 'none':
                    skip[attrName] = 1

                if attrName not in attributes:
                    attributes.append(attrName)

        for attrName in skip.iterkeys():
            try:
                attributes.remove(attrName)
            except:
                pass

        return attributes



class OneTimeShare(Share):
    """
    Delete format, conduit, and share after the first get or put.
    """

    def remove(self):
        self.conduit.delete(True)
        self.format.delete(True)
        self.delete(True)

    def put(self, updateCallback=None):
        super(OneTimeShare, self).put(updateCallback=updateCallback)
        collection = self.contents
        self.remove()
        return collection

    def get(self, updateCallback=None):
        super(OneTimeShare, self).get(updateCallback=updateCallback)
        collection = self.contents
        self.remove()
        return collection



class ShareConduit(pim.ContentItem):
    """
    Transfers items in and out.
    """

    def __init__(self, *args, **kw):
        super(ShareConduit, self).__init__(*args, **kw)
        self.marker = Item('marker', self, None)

    schema.kindInfo(displayName = u"Share Conduit Kind")

    share = schema.One(Share, inverse = Share.conduit)

    sharePath = schema.One(
        schema.Text,
        doc = "The parent 'directory' of the share",
    )

    shareName = schema.One(
        schema.Text, initialValue=u"",
        doc = "The 'directory' name of the share, relative to 'sharePath'",
    )

    manifest = schema.Mapping(
        schema.Dictionary,
        doc = "Keeps track of 'remote' item information, such as last "
              "modified date or ETAG",
        initialValue = {}
    )

    marker = schema.One(schema.SingleRef)




    def _conditionalPutItem(self, item, changes, updateCallback=None):
        """
        Put an item if it's not on the server or is out of date
        """
        result = 'skipped'

        if not self.share.format.acceptsItem(item):
            return result

        # Assumes that self.resourceList has been populated:
        externalItemExists = self._externalItemExists(item)

        logger.debug("Examining for put: %s, version=%d",
            item.getItemDisplayName().encode('ascii', 'replace'),
            item.getVersion())

        if not externalItemExists:
            result = 'added'
            needsUpdate = True

        else:
            needsUpdate = False

            # Check to see if the item or any of its itemCloud items have a
            # more recent version than the last time we synced
            for relatedItem in item.getItemCloud('sharing'):
                if relatedItem.itsUUID in changes:
                    modifiedAttributes = changes[relatedItem.itsUUID]
                    sharedAttributes = \
                        self.share.getSharedAttributes(relatedItem)
                    logger.debug("Changes for %s: %s", relatedItem.getItemDisplayName().encode('ascii', 'replace'), modifiedAttributes)
                    for change in modifiedAttributes:
                        if change in sharedAttributes:
                            logger.debug("A shared attribute (%s) changed for %s", change, relatedItem.getItemDisplayName().encode('ascii', 'replace'))
                            needsUpdate = True
                            result = 'modified'
                            break

        if needsUpdate:
            logger.info("...putting '%s' %s (%d vs %d) (on server: %s)" % \
             (item.getItemDisplayName().encode('ascii', 'replace'), item.itsUUID,
              item.getVersion(), self.marker.getVersion(), externalItemExists))

            if updateCallback and updateCallback(msg="'%s'" %
                item.getItemDisplayName()):
                raise SharingError(_(u"Cancelled by user"))

            data = self._putItem(item)

            if data is not None:
                self._addToManifest(self._getItemPath(item), item, data)
                logger.info("...done, data: %s, version: %d" %
                 (data, item.getVersion()))

                self.share.items.append(item)
            else:
                return 'skipped'

        try:
            del self.resourceList[self._getItemPath(item)]
        except:
            logger.info("...external item %s didn't previously exist" % \
                self._getItemPath(item))

        return result



    def _put(self, updateCallback=None):
        """
        Transfer entire 'contents', transformed, to server.
        """

        view = self.itsView

        location = self.getLocation()
        logger.info("Starting PUT of %s" % (location))

        try:
            contentsName = "'%s' (%s)" % (self.share.contents.displayName,
                location)
        except:
            # contents is either not set, is None, or has no displayName
            contentsName = location

        if updateCallback and updateCallback(msg=_(u"Uploading to "
            "%(name)s...") % { 'name' : contentsName } ):
            raise SharingError(_(u"Cancelled by user"))

        stats = {
            'share' : self.share.itsUUID,
            'op' : 'put',
            'added' : [],
            'modified' : [],
            'removed' : []
        }

        self.connect()

        # share.filterClasses includes the dotted names of classes so
        # they can be shared.
        filterClasses = self._getFilterClasses()

        style = self.share.format.fileStyle()
        if style == ImportExportFormat.STYLE_DIRECTORY:

            self.resourceList = \
                self._getResourceList(location)

            # logger.debug("Resources on server: %(resources)s" %
            #     {'resources':self.resourceList})
            # logger.debug("Manifest: %(manifest)s" %
            #     {'manifest':self.manifest})

            # Ignore any resources which we weren't able to parse during
            # a previous GET -- they're the ones in our manifest with
            # None as a uuid:
            for (path, record) in self.manifest.iteritems():
                if record['uuid'] is None:
                    if self.resourceList.has_key(path):
                        logger.debug('Removing an unparsable resource from the resourceList: %(path)s' % { 'path' : path })
                        del self.resourceList[path]

            # Build the list of local changes
            prevVersion = self.marker.getVersion()
            changes = localChanges(view, prevVersion, view.itsVersion)

            # If we're sharing a collection, put the collection's items
            # individually:
            if isinstance(self.share.contents, pim.AbstractCollection):

                #
                # Remove any resources from the server that aren't in
                # our collection anymore.  The reason we have to do this
                # first is because if one .ics resource is replacing
                # another (on a CalDAV server) and they have the same
                # icalUID, the CalDAV server won't allow them to exist
                # simultaneously.
                # Any items that are in the manifest but not in the
                # collection are the ones to remove.

                removeFromManifest = []

                for (path, record) in self.manifest.iteritems():
                    if path in self.resourceList:
                        uuid = record['uuid']
                        if uuid:
                            item = view.findUUID(uuid)

                            if item is not self.share and (
                                item is None or
                                item not in self.share.contents or (
                                    filterClasses and
                                    not isinstance(item, filterClasses)
                                )
                            ):

                                if updateCallback and updateCallback(msg=_(u"Removing item from server: '%(path)s'") % { 'path' : path }):
                                    raise SharingError(_(u"Cancelled by user"))
                                self._deleteItem(path)
                                del self.resourceList[path]
                                removeFromManifest.append(path)
                                logger.debug('Item removed locally, so removing from server: %(path)s' % { 'path' : path })
                                stats['removed'].append(uuid)

                for path in removeFromManifest:
                    self._removeFromManifest(path)

                # logger.debug("Manifest: %(manifest)s" %
                #     {'manifest':self.manifest})


                for item in self.share.contents:

                    if updateCallback and updateCallback(work=True):
                        raise SharingError(_(u"Cancelled by user"))

                    # Skip private items
                    if item.private:
                        continue

                    # Skip any items not matching the filtered classes
                    if filterClasses and not isinstance(item, filterClasses):
                        continue

                    # Put the item
                    result = self._conditionalPutItem(item, changes,
                        updateCallback=updateCallback)
                    if result in ('added', 'modified'):
                        stats[result].append(item.itsUUID)


            # Put the Share item itself
            result = self._conditionalPutItem(self.share, changes,
                updateCallback=updateCallback)
            if result in ('added', 'modified'):
                stats[result].append(self.share.itsUUID)


        elif style == ImportExportFormat.STYLE_SINGLE:
            # Put a monolithic file representing the share item.
            #@@@MOR This should be beefed up to only publish if at least one
            # of the items has changed.
            self._putItem(self.share)


        self.disconnect()

        logger.info("Finished PUT of %s %s", location, stats)

        return stats



    def _conditionalGetItem(self, itemPath, into=None, changes=None,
        previousView=None, updateCallback=None):
        """
        Get an item from the server if we don't yet have it or our copy
        is out of date
        """

        # assumes self.resourceList is populated

        if itemPath not in self.resourceList:
            logger.info("...Not on server: %s" % itemPath)
            return None

        if not self._haveLatest(itemPath):
            # logger.info("...getting: %s" % itemPath)

            (item, data) = self._getItem(itemPath, into=into, changes=changes,
                previousView=previousView, updateCallback=updateCallback)

            if item is not None:
                self._addToManifest(itemPath, item, data)
                self._setFetched(itemPath)
                logger.info("...imported '%s' '%s' %s, data: %s" % \
                 (itemPath, item.getItemDisplayName().encode('ascii',
                    'replace'), item, data))

                self.share.items.append(item)
                if updateCallback and updateCallback(msg="'%s'" %
                    item.getItemDisplayName()):
                    raise SharingError(_(u"Cancelled by user"))

                return item

            logger.error("...NOT able to import '%s'" % itemPath)
            # Record with no item, indicating an error
            self._addToManifest(itemPath)

        return None




    def _get(self, previousView=None, updateCallback=None, getPhrase=None):

        location = self.getLocation()
        logger.info("Starting GET of %s" % (location))

        try:
            contentsName = "'%s' (%s)" % (self.share.contents.displayName,
                location)
        except:
            # contents is either not set, is None, or has no displayName
            contentsName = location

        if getPhrase is None:
            getPhrase = _(u"Downloading from %(name)s...")
        if updateCallback and updateCallback(msg=getPhrase %
            { 'name' : contentsName } ):
            raise SharingError(_(u"Cancelled by user"))

        view = self.itsView

        stats = {
            'share' : self.share.itsUUID,
            'op' : 'get',
            'added' : [],
            'modified' : [],
            'removed' : []
        }

        # Build the list of local changes
        prevVersion = self.marker.getVersion()
        changes = localChanges(view, prevVersion, view.itsVersion)

        self.connect()

        if not self.exists():
            raise NotFound(_(u"%(location)s does not exist") %
                {'location': location})

        self.resourceList = self._getResourceList(location)

        # logger.debug("Resources on server: %(resources)s" %
        #     {'resources':self.resourceList})
        # logger.debug("Manifest: %(manifest)s" %
        #     {'manifest':self.manifest})

        # We need to keep track of which items we've seen on the server so
        # we can tell when one has disappeared.
        self._resetFlags()

        itemPath = self._getItemPath(self.share)
        # if itemPath is None, the Format we're using doesn't have a file
        # that represents the Share item (CalDAV, for instance).

        if itemPath:
            # Get the file that represents the Share item

            if updateCallback and updateCallback(work=True):
                raise SharingError(_(u"Cancelled by user"))

            item = self._conditionalGetItem(itemPath, into=self.share,
                changes=changes, previousView=previousView,
                updateCallback=updateCallback)

            if item is not None:
                if item.itsVersion > 0 :
                    stats['added'].append(item.itsUUID)
                else:
                    stats['modified'].append(item.itsUUID)

            # Whenever we get an item, mark it seen in our manifest and remove
            # it from the server resource list:
            self._setSeen(itemPath)
            try:
                del self.resourceList[itemPath]
            except:
                pass

        # Make sure we don't subscribe to a KindCollection, since some evil
        # person could slip you a KindCollection that would fill itself with
        # your items.
        if isinstance(self.share.contents, pim.KindCollection):
            raise SharingError(_(u"Subscribing to KindCollections prohibited"))

        # Make sure we have a collection to add items to:
        if self.share.contents is None:
            self.share.contents = pim.InclusionExclusionCollection(itsView=view).setup()

        contents = self.share.contents

        # If share.contents is an AbstractCollection, treat other resources as
        # items to add to the collection:
        if isinstance(contents, pim.AbstractCollection):

            # Make sure the collection item is properly set up:

            if isinstance(contents, pim.ListCollection) and \
                not hasattr(contents, 'rep'):
                    contents.rep = Set((contents,'refCollection'))
                    contents.setup() # make sure a color is assigned

            if isinstance(contents, pim.InclusionExclusionCollection) and \
                not hasattr(contents, 'rep'):
                    contents.setup()

            filterClasses = self._getFilterClasses()


            # If an item is in the manifest but it's no longer in the
            # collection, we need to skip the server's copy -- we'll
            # remove it during the PUT phase
            for (path, record) in self.manifest.iteritems():
                if path in self.resourceList:
                    uuid = record['uuid']
                    if uuid:
                        item = view.findUUID(uuid)
                        if item is None or \
                            item not in self.share.contents:
                            del self.resourceList[path]
                            self._setSeen(path)
                            logger.debug("Item removed locally, so not "
                                "fetching from server: %(path)s" %
                                { 'path' : path } )


            # Conditionally fetch items, and add them to collection
            for itemPath in self.resourceList:

                if updateCallback and updateCallback(work=True):
                    raise SharingError(_(u"Cancelled by user"))

                item = self._conditionalGetItem(itemPath, changes=changes,
                    previousView=previousView,
                    updateCallback=updateCallback)

                if item is not None:
                    self.share.contents.add(item)

                    if item.itsVersion == 0 :
                        stats['added'].append(item.itsUUID)
                    else:
                        stats['modified'].append(item.itsUUID)

                self._setSeen(itemPath)

            # When first importing a collection, name it after the share
            if not hasattr(self.share.contents, 'displayName'):
                self.share.contents.displayName = \
                    self.share.displayName

            # If an item was previously on the server (it was in our
            # manifest) but is no longer on the server, remove it from
            # the collection locally:
            toRemove = []
            for unseenPath in self._iterUnseen():
                uuid = self.manifest[unseenPath]['uuid']
                if uuid:
                    item = view.findUUID(uuid)
                    if item is not None:

                        # If an item has disappeared from the server, only
                        # remove it locally if it matches the current share
                        # filter.

                        if not filterClasses or isinstance(item, filterClasses):

                            logger.info("...removing %s from collection" % item)
                            if item in self.share.contents:
                                self.share.contents.remove(item)
                            if item in self.share.items:
                                self.share.items.remove(item)
                            stats['removed'].append(item.itsUUID)
                            if updateCallback and updateCallback(
                                msg=_(u"Removing from collection: '%(name)s'")
                                % { 'name' : item.getItemDisplayName() }
                                ):
                                raise SharingError(_(u"Cancelled by user"))

                else:
                    logger.info("Removed an unparsable resource manifest entry for %s", unseenPath)

                # In any case, remove from manifest
                toRemove.append(unseenPath)

            for removePath in toRemove:
                self._removeFromManifest(removePath)

        self.disconnect()

        logger.info("Finished GET of %s %s", location, stats)

        return stats


    def _getFilterClasses(self):
        return tuple(schema.importString(classString) for classString in
            self.share.filterClasses)


    def _getItemPath(self, item):
        """
        Return a string that uniquely identifies a resource in the remote
        share, such as a URL path or a filesystem path.  These strings
        will be used for accessing the manifest and resourceList dicts.
        """
        extension = self.share.format.extension(item)
        style = self.share.format.fileStyle()
        if style == ImportExportFormat.STYLE_DIRECTORY:
            if isinstance(item, Share):
                path = self.share.format.shareItemPath()
            else:
                for (path, record) in self.manifest.iteritems():
                    if record['uuid'] == item.itsUUID:
                        return path

                path = "%s.%s" % (item.itsUUID, extension)

            return path

        elif style == ImportExportFormat.STYLE_SINGLE:
            return self.shareName

        else:
            print "@@@MOR Raise an exception here"


    # Manifest mangement routines
    # The manifest keeps track of the state of shared items at the time of
    # last sync.  It is a dictionary keyed on "path" (not repo path, but
    # path at the external source), whose values are dictionaries containing
    # the item's internal UUID, external UUID, either a last-modified date
    # (if filesystem) or ETAG (if webdav), and the item's version (as in
    # what item.getVersion() returns)
    # 
    # If we tried to get an item but the transform failed, we add that resource
    # to the manifest with "" as the uuid

    def _clearManifest(self):
        self.manifest = {}

    def _addToManifest(self, path, item=None, data=None):
        # data is an ETAG, or last modified date

        if item is None:
            uuid = None
        else:
            uuid = item.itsUUID

        self.manifest[path] = {
         'uuid' : uuid,
         'data' : data,
        }


    def _removeFromManifest(self, path):
        try:
            del self.manifest[path]
        except:
            pass

    def _externalItemExists(self, item):
        itemPath = self._getItemPath(item)
        return itemPath in self.resourceList

    def _haveLatest(self, path, data=None):
        """
        Do we have the latest copy of this item?
        """
        if data == None:
            data = self.resourceList[path]['data']
        try:
            record = self.manifest[path]
            if record['data'] == data:
                # logger.info("haveLatest: Yes (%s %s)" % (path, data))
                return True
            else:
                # print "MISMATCH: local=%s, remote=%s" % (record['data'], data)
                logger.info("...don't have latest (%s local:%s remote:%s)" % (path,
                 record['data'], data))
                return False
        except KeyError:
            pass

        logger.info("...don't yet have %s" % path)
        return False

    def _resetFlags(self):
        for value in self.manifest.itervalues():
            value['seen'] = False
            value['fetched'] = False

    def _setSeen(self, path):
        try:
            self.manifest[path]['seen'] = True
        except:
            pass

    def _setFetched(self, path):
        try:
            self.manifest[path]['fetched'] = True
        except:
            pass

    def _wasFetched(self, path):
        try:
            return self.manifest[path]['fetched']
        except:
            return False

    def _iterUnseen(self):
        for (path, value) in self.manifest.iteritems():
            if not value['seen']:
                yield path


    def getCount(self):
        return len(self._getResourceList(self.getLocation()))

    # Methods that subclasses *must* implement:

    def getLocation(self, privilege=None):
        """
        Return a string representing where the share is being exported
        to or imported from, such as a URL or a filesystem path
        """
        pass

    def _getResourceList(self, location):
        """
        Return a dictionary representing what items exist in the remote
        share.
        """
        # 'location' is a location returned from getLocation
        # The returned dictionary should be keyed on a string that uniquely
        # identifies a resource in the remote share.  For example, a url
        # path or filesystem path.  The values of the dictionary should
        # be dictionaries of the format { 'data' : <string> } where <string>
        # is some piece of data that encapsulates version information for
        # the remote resources (such as a last modified date, or an ETag).
        pass

    def _putItem(self, item, where):
        """
        Must implement
        """
        pass

    def _deleteItem(self, itemPath):
        """
        Must implement
        """
        pass

    def _getItem(self, itemPath, into=None, changes=None, previousView=None,
        updateCallback=None):
        """
        Must implement
        """
        pass

    def connect(self):
        pass

    def disconnect(self):
        pass

    def exists(self):
        pass

    def create(self):
        """
        Create the share on the server.
        """
        pass

    def destroy(self):
        """
        Remove the share from the server.
        """
        pass

    def open(self):
        """
        Open the share for access.
        """
        pass

    def close(self):
        """
        Close the share.
        """
        pass


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

class FileSystemConduit(ShareConduit):

    schema.kindInfo(displayName=u"File System Share Conduit Kind")


    def __init__(self, *args, **kw):
        if 'shareName' not in kw:
            kw['shareName'] = unicode(UUID())
        super(FileSystemConduit, self).__init__(*args, **kw)

        # @@@MOR What sort of processing should we do on sharePath for this
        # filesystem conduit?

        # @@@MOR Probably should remove any slashes, or warn if there are any?
        self.shareName = self.shareName.strip("/")

    def getLocation(self, privilege=None):
        if self.hasLocalAttributeValue("sharePath") and \
         self.hasLocalAttributeValue("shareName"):
            return os.path.join(self.sharePath, self.shareName)
        raise Misconfigured(_(u"A misconfiguration error was encountered"))

    def _get(self, previousView=None, updateCallback=None, getPhrase=None):
        if getPhrase is None:
            getPhrase = _(u"Importing from %(name)s...")
        return super(FileSystemConduit, self)._get(previousView, updateCallback,
                                                   getPhrase)

    def _putItem(self, item):
        path = self._getItemFullPath(self._getItemPath(item))

        try:
            text = self.share.format.exportProcess(item)
        except Exception, e:
            logging.exception(e)
            raise TransformationFailed(_(u"Transformation error: see chandler.log for more information"))

        if text is None:
            return None
        out = file(path, 'wb') #outputting in binary mode to preserve ics CRLF
        out.write(text)
        out.close()
        stat = os.stat(path)
        return stat.st_mtime

    def _deleteItem(self, itemPath):
        path = self._getItemFullPath(itemPath)

        logger.info("...removing from disk: %s" % path)
        os.remove(path)

    def _getItem(self, itemPath, into=None, changes=None, previousView=None,
        updateCallback=None):

        view = self.itsView

        # logger.info("Getting item: %s" % itemPath)
        path = self._getItemFullPath(itemPath)

        extension = os.path.splitext(path)[1].strip(os.path.extsep)
        text = file(path).read()

        try:
            item = self.share.format.importProcess(text,
                extension=extension, item=into, changes=changes,
                previousView=previousView,
                updateCallback=updateCallback)
        except Exception, e:
            logging.exception(e)
            raise TransformationFailed(_(u"Transformation error: see chandler.log for more information"))

        stat = os.stat(path)
        return (item, stat.st_mtime)

    def _getResourceList(self, location):
        fileList = {}

        style = self.share.format.fileStyle()
        if style == ImportExportFormat.STYLE_DIRECTORY:
            for filename in os.listdir(location):
                fullPath = os.path.join(location, filename)
                stat = os.stat(fullPath)
                fileList[filename] = { 'data' : stat.st_mtime }

        elif style == ImportExportFormat.STYLE_SINGLE:
            stat = os.stat(location)
            fileList[self.shareName] = { 'data' : stat.st_mtime }

        else:
            print "@@@MOR Raise an exception here"

        return fileList

    def _getItemFullPath(self, path):
        style = self.share.format.fileStyle()
        if style == ImportExportFormat.STYLE_DIRECTORY:
            path = os.path.join(self.sharePath, self.shareName, path)
        elif style == ImportExportFormat.STYLE_SINGLE:
            path = os.path.join(self.sharePath, self.shareName)
        return path


    def exists(self):
        super(FileSystemConduit, self).exists()

        style = self.share.format.fileStyle()
        if style == ImportExportFormat.STYLE_DIRECTORY:
            return os.path.isdir(self.getLocation())
        elif style == ImportExportFormat.STYLE_SINGLE:
            return os.path.isfile(self.getLocation())
        else:
            print "@@@MOR Raise an exception here"

    def create(self):
        super(FileSystemConduit, self).create()

        if self.exists():
            raise AlreadyExists(_(u"Share path already exists"))

        if self.sharePath is None or not os.path.isdir(self.sharePath):
            raise Misconfigured(_(u"Share path is not set, or path doesn't exist"))

        style = self.share.format.fileStyle()
        if style == ImportExportFormat.STYLE_DIRECTORY:
            path = self.getLocation()
            if not os.path.exists(path):
                os.mkdir(path)

    def destroy(self):
        super(FileSystemConduit, self).destroy()

        path = self.getLocation()

        if not self.exists():
            raise NotFound(_(u"%(path)s does not exist") % {'path': path})

        style = self.share.format.fileStyle()
        if style == ImportExportFormat.STYLE_DIRECTORY:
            for filename in os.listdir(path):
                os.remove(os.path.join(path, filename))
            os.rmdir(path)
        elif style == ImportExportFormat.STYLE_SINGLE:
            os.remove(path)


    def open(self):
        super(FileSystemConduit, self).open()

        path = self.getLocation()

        if not self.exists():
            raise NotFound(_(u"%(path)s does not exist") % {'path': path})

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

class WebDAVConduit(ShareConduit):

    schema.kindInfo(displayName=u"WebDAV Share Conduit Kind")

    account = schema.One('WebDAVAccount', inverse='conduits',initialValue=None)
    host = schema.One(schema.Text, initialValue=u"")
    port = schema.One(schema.Integer, initialValue=80)
    username = schema.One(schema.Text, initialValue=u"")
    password = schema.One(schema.Text, initialValue=u"")
    useSSL = schema.One(schema.Boolean, initialValue=False)

    # The ticket this conduit will use (we're a sharee and we're using this)
    ticket = schema.One(schema.Text, initialValue="")

    # The tickets we generated if we're a sharer
    ticketReadOnly = schema.One(schema.Text, initialValue="")
    ticketReadWrite = schema.One(schema.Text, initialValue="")

    def __init__(self, *args, **kw):
        if 'shareName' not in kw:
            kw['shareName'] = unicode(UUID())
        super(WebDAVConduit, self).__init__(*args, **kw)
        # @@@MOR Probably should remove any slashes, or warn if there are
        # any?
        self.shareName = self.shareName.strip("/")
        self.onItemLoad()

    def onItemLoad(self, view=None):
        self.serverHandle = None

    def _getSettings(self):
        if self.account is None:
            return (self.host, self.port, self.sharePath.strip("/"),
                    self.username, self.password, self.useSSL)
        else:
            return (self.account.host, self.account.port,
                    self.account.path.strip("/"), self.account.username,
                    self.account.password, self.account.useSSL)

    def _getServerHandle(self):
        # @@@ [grant] Collections and the trailing / issue.
        if self.serverHandle == None:
            # logger.debug("...creating new webdav ServerHandle")
            (host, port, sharePath, username, password, useSSL) = \
            self._getSettings()

            self.serverHandle = WebDAV.ChandlerServerHandle(host, port=port,
                username=username, password=password, useSSL=useSSL,
                repositoryView=self.itsView)

        return self.serverHandle

    def _releaseServerHandle(self):
        self.serverHandle = None

    def getLocation(self, privilege=None):
        """
        Return the url of the share
        """

        (host, port, sharePath, username, password, useSSL) = \
            self._getSettings()
        if useSSL:
            scheme = u"https"
            defaultPort = 443
        else:
            scheme = u"http"
            defaultPort = 80

        if port == defaultPort:
            url = u"%s://%s" % (scheme, host)
        else:
            url = u"%s://%s:%d" % (scheme, host, port)
        url = urlparse.urljoin(url, sharePath + "/")
        url = urlparse.urljoin(url, self.shareName)

        if privilege == 'readonly':
            if self.ticketReadOnly:
                url = url + u"?ticket=%s" % self.ticketReadOnly
        elif privilege == 'readwrite':
            if self.ticketReadWrite:
                url = url + u"?ticket=%s" % self.ticketReadWrite
        elif privilege == 'subscribed':
            if self.ticket:
                url = url + u"?ticket=%s" % self.ticket

        return url

    def _getSharePath(self):
        return "/" + self._getSettings()[2]

    def _resourceFromPath(self, path):
        serverHandle = self._getServerHandle()
        sharePath = self._getSharePath()

        if sharePath == u"/":
            sharePath = u"" # Avoid double-slashes on next line...
        resourcePath = u"%s/%s" % (sharePath, self.shareName)

        if self.share.format.fileStyle() == ImportExportFormat.STYLE_DIRECTORY:
            resourcePath += "/" + path

        resource = serverHandle.getResource(resourcePath)

        if getattr(self, 'ticket', False):
            resource.ticketId = self.ticket
        return resource

    def exists(self):
        result = super(WebDAVConduit, self).exists()

        resource = self._resourceFromPath(u"")

        try:
            result = self._getServerHandle().blockUntil(resource.exists)
        except zanshin.error.ConnectionError, err:
            raise CouldNotConnect(_(u"Unable to connect to server. Received the following error: %(error)s") % {'error': err.args[0]})
        except M2Crypto.BIO.BIOError, err:
            raise CouldNotConnect(_(u"Unable to connect to server. Received the following error: %(error)s") % {'error': err})
        except zanshin.webdav.PermissionsError, err:
            message = _(u"Not authorized to PUT %(info)s") % {'info': self.getLocation()}
            logging.exception(err)
            raise NotAllowed(message)


        return result

    def _createCollectionResource(self, handle, resource, childName):
        return handle.blockUntil(resource.createCollection, childName)

    def create(self):
        super(WebDAVConduit, self).create()

        style = self.share.format.fileStyle()

        if style == ImportExportFormat.STYLE_DIRECTORY:
            url = self.getLocation()
            handle = self._getServerHandle()
            try:
                if url[-1] != '/': url += '/'

                # need to get resource representing the parent of the
                # collection we want to create

                # Get the parent directory of the given path:
                # '/dev1/foo/bar' becomes ['dev1', 'foo', 'bar']
                path = url.strip('/').split('/')
                parentPath = path[:-1]
                childName = path[-1]
                # ['dev1', 'foo'] becomes "dev1/foo"
                url = "/".join(parentPath)
                resource = handle.getResource(url)
                if getattr(self, 'ticket', False):
                    resource.ticketId = self.ticket

                child = self._createCollectionResource(handle, resource,
                    childName)

            except zanshin.webdav.ConnectionError, err:
                raise CouldNotConnect(_(u"Unable to connect to server. Received the following error: %(error)s") % {'error': err})
            except M2Crypto.BIO.BIOError, err:
                raise CouldNotConnect(_(u"Unable to connect to server. Received the following error: %(error)s") % {'error': err})
            except zanshin.http.HTTPError, err:
                logger.error('Received status %d attempting to create %s',
                             err.status, self.getLocation())

                if err.status == twisted.web.http.NOT_ALLOWED:
                    # already exists
                    message = _(u"Collection at %(url)s already exists") % {'url': url}
                    raise AlreadyExists(message)

                if err.status == twisted.web.http.UNAUTHORIZED:
                    # not authorized
                    message = _(u"Not authorized to create collection %(url)s") % {'url': url}
                    raise NotAllowed(message)

                if err.status == twisted.web.http.CONFLICT:
                    # this happens if you try to create a collection within a
                    # nonexistent collection
                    (host, port, sharePath, username, password, useSSL) = \
                        self._getSettings()
                    message = _(u"The directory '%(directoryName)s' could not be found on %(server)s.\nPlease verify the Path setting in your %(accountType)s account") % {'directoryName': sharePath, 'server': host,
                                                        'accountType': 'WebDAV'}
                    raise NotFound(message)

                if err.status == twisted.web.http.FORBIDDEN:
                    # the server doesn't allow the creation of a collection here
                    message = _(u"Server doesn't allow the creation of collections at %(url)s") % {'url': url}
                    raise IllegalOperation(message)
                    
                if err.status == twisted.web.http.PRECONDITION_FAILED:
                    message = _(u"The contents of %(url)s were modified unexpectedly on the server while trying to share.") % {'url':url}
                    raise IllegalOperation(message)

                if err.status != twisted.web.http.CREATED:
                     message = _(u"WebDAV error, status = %(statusCode)d") % {'statusCode': err.status}
                     raise IllegalOperation(message)

    def destroy(self):
        if self.exists():
            self._deleteItem(u"")

    def open(self):
        super(WebDAVConduit, self).open()

    def _getContainerResource(self):

        serverHandle = self._getServerHandle()

        style = self.share.format.fileStyle()

        if style == ImportExportFormat.STYLE_DIRECTORY:
            path = self.getLocation()
        else:
            path = self._getSharePath()

        # Make sure we have a container
        if path and path[-1] != '/':
            path += '/'

        resource = serverHandle.getResource(path)
        if getattr(self, 'ticket', False):
            resource.ticketId = self.ticket
        return resource


    def _putItem(self, item):
        """
        putItem should publish an item and return etag/date, etc.
        """

        try:
            text = self.share.format.exportProcess(item)
        except Exception, e:
            logging.exception(e)
            msg = _(u"Transformation failed for %(item)s") % {'item': item}
            raise TransformationFailed(msg)

        if text is None:
            return None

        contentType = self.share.format.contentType(item)
        itemName = self._getItemPath(item)
        container = self._getContainerResource()

        try:
            # @@@MOR For some reason, when doing a PUT on the rpi server, I
            # can see it's returning 400 Bad Request, but zanshin doesn't
            # seem to be raising an exception.  Putting in a check for
            # newResource == None as another indicator that it failed to
            # create the resource
            newResource = None
            serverHandle = self._getServerHandle()

            # Here, if the resource doesn't exist on the server, we're
            # going to call container.createFile(), which will fail
            # with a 412 (PRECONDITION_FAILED) iff something already
            # exists at that location.
            #
            # If the resource does exist, we get hold of it, and
            # call resource.put(), which fails with a 412 iff the
            # etag of the resource changed.

            ## if not self.resourceList.has_key(itemName):
            ##     newResource = serverHandle.blockUntil(
            ##                       container.createFile, itemName, body=text,
            ##                       type=contentType)
            ## else:
            resourcePath = container.path + itemName
            resource = serverHandle.getResource(resourcePath)

            if getattr(self, 'ticket', False):
                resource.ticketId = self.ticket

            serverHandle.blockUntil(resource.put, text, checkETag=False,
                                    contentType=contentType)

            # We're using newResource of None to track errors
            newResource = resource

        except zanshin.webdav.ConnectionError, err:
            raise CouldNotConnect(_(u"Unable to connect to server. Received the following error: %(error)s") % {'error': err})
        except M2Crypto.BIO.BIOError, err:
            raise CouldNotConnect(_(u"Unable to connect to server. Received the following error: %(error)s") % {'error': err})
        # 201 = new, 204 = overwrite

        except zanshin.webdav.PermissionsError:
            message = _(u"Not authorized to PUT %(info)s") % {'info': itemName}
            raise NotAllowed(message)

        except zanshin.webdav.WebDAVError, err:

            if err.status in (twisted.web.http.FORBIDDEN,
                              twisted.web.http.CONFLICT,
                              twisted.web.http.PRECONDITION_FAILED):
                # [@@@] grant: Should probably come up with a better message
                # for PRECONDITION_FAILED (an ETag conflict).
                # seen if trying to PUT to a nonexistent collection (@@@MOR verify)
                message = _(u"Publishing %(itemName)s failed; server rejected our request with status %(status)d") % {'itemName': itemName, 'status': err.status}
                raise NotAllowed(message)

        if newResource is None:
            message = _(u"Not authorized to PUT %(itemName)s") % {'itemName': itemName}
            raise NotAllowed(message)

        etag = newResource.etag

        # @@@ [grant] Get mod-date?
        return etag

    def _deleteItem(self, itemPath):
        resource = self._resourceFromPath(itemPath)
        logger.info("...removing from server: %s" % resource.path)

        if resource != None:
            try:
                deleteResp = self._getServerHandle().blockUntil(resource.delete)
            except zanshin.webdav.ConnectionError, err:
                raise CouldNotConnect(_(u"Unable to connect to server. Received the following error: %(error)s") % {'error': err})
            except M2Crypto.BIO.BIOError, err:
                raise CouldNotConnect(_(u"Unable to connect to server. Received the following error: %(error)s") % {'error': err})

    def _getItem(self, itemPath, into=None, changes=None, previousView=None,
        updateCallback=None):
        view = self.itsView
        resource = self._resourceFromPath(itemPath)

        try:
            resp = self._getServerHandle().blockUntil(resource.get)

        except zanshin.webdav.ConnectionError, err:
            raise CouldNotConnect(_(u"Unable to connect to server. Received the following error: %(error)s") % {'error': err})
        except M2Crypto.BIO.BIOError, err:
            raise CouldNotConnect(_(u"Unable to connect to server. Received the following error: %(error)s") % {'error': err})

        if resp.status == twisted.web.http.NOT_FOUND:
            message = _(u"Path %(path)s not found") % {'path': resource.path}
            raise NotFound(message)

        if resp.status == twisted.web.http.UNAUTHORIZED:
            message = _(u"Not authorized to GET %(path)s") % {'path': resource.path}
            raise NotAllowed(message)

        text = resp.body

        etag = resource.etag

        try:
            item = self.share.format.importProcess(text, item=into,
                changes=changes, previousView=previousView,
                updateCallback=updateCallback)
        except VersionMismatch:
            raise
        except Exception, e:
            logger.exception("Failed to parse XML for item %s: '%s'" %
                (itemPath, text.encode('ascii', 'replace')))
            raise TransformationFailed(_(u"%(itemPath)s %(error)s (See chandler.log for text)") % \
                                       {'itemPath': itemPath, 'error': e})

        return (item, etag)


    def _getResourceList(self, location): # must implement
        """
        Return information (etags) about all resources within a collection
        """

        resourceList = {}

        style = self.share.format.fileStyle()

        if style == ImportExportFormat.STYLE_DIRECTORY:
            shareCollection = self._getContainerResource()

            try:
                children = self._getServerHandle().blockUntil(
                                shareCollection.getAllChildren)

            except zanshin.webdav.ConnectionError, err:
                raise CouldNotConnect(_(u"Unable to connect to server. Received the following error: %(error)s") % {'error': err})
            except M2Crypto.BIO.BIOError, err:
                raise CouldNotConnect(_(u"Unable to connect to server. Received the following error: %(error)s") % {'error': err})
            except zanshin.webdav.WebDAVError, e:

                if e.status == twisted.web.http.NOT_FOUND:
                    raise NotFound(_(u"Path %(path)s not found") % {'path': shareCollection.path})

                if e.status == twisted.web.http.UNAUTHORIZED:
                    raise NotAllowed(_(u"Not authorized to get %(path)s") % {'path': shareCollection.path})

                raise SharingError(_(u"The following sharing error occurred: %(error)s") % {'error': e})


            for child in children:
                if child != shareCollection:
                    path = child.path.split("/")[-1]
                    etag = child.etag
                    # if path is empty, it's a subcollection (skip it)
                    if path:
                        resourceList[path] = { 'data' : etag }

        elif style == ImportExportFormat.STYLE_SINGLE:
            resource = self._getServerHandle().getResource(location)
            if getattr(self, 'ticket', False):
                resource.ticketId = self.ticket
            # @@@ [grant] Error handling and reporting here
            # are crapski
            try:
                self._getServerHandle().blockUntil(resource.propfind, depth=0)
            except zanshin.webdav.ConnectionError, err:
                raise CouldNotConnect(_(u"Unable to connect to server. Received the following error: %(error)s") % {'error': err})
            except M2Crypto.BIO.BIOError, err:
                raise CouldNotConnect(_(u"Unable to connect to server. Received the following error: %(error)s") % {'error': err})
            except zanshin.webdav.PermissionsError, err:
                message = _(u"Not authorized to GET %(path)s") % {'path': location}
                raise NotAllowed(message)
#            except NotFoundError:
#                message = "Not found: %s" % url
#                raise NotFound(message=message)
#

            etag = resource.etag
            # @@@ [grant] count use resource.path here
            path = urlparse.urlparse(location)[2]
            path = path.split("/")[-1]
            resourceList[path] = { 'data' : etag }

        return resourceList

    def connect(self):
        self._releaseServerHandle()
        self._getServerHandle() # @@@ [grant] Probably not necessary

    def disconnect(self):
        self._releaseServerHandle()

    def createTickets(self):
        handle = self._getServerHandle()
        location = self.getLocation()
        if not location.endswith("/"):
            location += "/"
        resource = handle.getResource(location)

        ticket = handle.blockUntil(resource.createTicket)
        logger.debug("Read Only ticket: %s %s",
            ticket.ticketId, ticket.ownerUri)
        self.ticketReadOnly = ticket.ticketId

        ticket = handle.blockUntil(resource.createTicket, readonly=False)
        logger.debug("Read Write ticket: %s %s",
            ticket.ticketId, ticket.ownerUri)
        self.ticketReadWrite = ticket.ticketId

        return (self.ticketReadOnly, self.ticketReadWrite)

    def getTickets(self):
        handle = self._getServerHandle()
        location = self.getLocation()
        if not location.endswith("/"):
            location += "/"
        resource = handle.getResource(location)

        try:
            tickets = handle.blockUntil(resource.getTickets)
            for ticket in tickets:
                if ticket.readonly:
                    self.ticketReadOnly = ticket.ticketId
                else:
                    self.ticketReadWrite = ticket.ticketId

        except Exception, e:
            # Couldn't get tickets due to permissions problem, or there were
            # no tickets
            pass

    def setDisplayName(self, name):
        handle = self._getServerHandle()
        location = self.getLocation()
        if not location.endswith("/"):
            location += "/"
        resource = handle.getResource(location)
        handle.blockUntil(resource.setDisplayName, name)


class CalDAVConduit(WebDAVConduit):

    def _createCollectionResource(self, handle, resource, childName):
        return handle.blockUntil(resource.createCalendar, childName)

    def _putItem(self, item):
        result = super(CalDAVConduit, self)._putItem(item)

        displayName = item.getItemDisplayName()
        itemName = self._getItemPath(item)
        serverHandle = self._getServerHandle()
        container = self._getContainerResource()
        resourcePath = container.path + itemName
        resource = serverHandle.getResource(resourcePath)
        serverHandle.blockUntil(resource.setDisplayName, displayName)

        return result



class SimpleHTTPConduit(WebDAVConduit):
    """
    Useful for get-only subscriptions of remote .ics files
    """

    schema.kindInfo(displayName=u"Simple HTTP Share Conduit Kind")

    lastModified = schema.One(schema.Text, initialValue = '')

    def get(self, updateCallback=None):
        self._get(updateCallback=updateCallback)

    def _get(self, previousView=None, updateCallback=None):

        # @@@MOR: we need to have importProcess return stats about what it did.
        # Otherwise, since this is a monolithic .ics file, we don't know the
        # details other than we either fetched the .ics file or we didn't
        stats = {
            'share' : self.share.itsUUID,
            'op' : 'get',
            'added' : [],
            'modified' : [],
            'removed' : []
        }

        prevVersion = self.marker.getVersion()
        view = self.itsView
        changes = localChanges(view, prevVersion, view.itsVersion)

        location = self.getLocation()
        if updateCallback and updateCallback(msg=_(u"Checking for update: '%(location)s'") % { 'location' : location } ):
            raise SharingError(_(u"Cancelled by user"))

        self.connect()
        logger.info("Starting GET of %s" % (location))
        extraHeaders = { }
        if self.lastModified:
            extraHeaders['If-Modified-Since'] = self.lastModified
            logger.info("...last modified: %s" % self.lastModified)

        try:
            handle = self._getServerHandle()
            resp = handle.blockUntil(handle.get, location,
                                    extraHeaders=extraHeaders)

            if resp.status == twisted.web.http.NOT_MODIFIED:
                # The remote resource is as we saw it before
                if updateCallback and updateCallback(msg=_(u"Not modified")):
                    raise SharingError(_(u"Cancelled by user"))
                logger.info("...not modified")
                return stats

            if updateCallback and updateCallback(msg='%s' % location):
                raise SharingError(_(u"Cancelled by user"))

        except zanshin.webdav.ConnectionError, err:
            raise CouldNotConnect(_(u"Unable to connect to server. Received the following error: %(error)s") % {'error': err})
        except M2Crypto.BIO.BIOError, err:
            raise CouldNotConnect(_(u"Unable to connect to server. Received the following error: %(error)s") % {'error': err})

        if resp.status == twisted.web.http.NOT_FOUND:
            raise NotFound(_(u"%(location)s does not exist") % {'location': location})

        if resp.status == twisted.web.http.UNAUTHORIZED:
            message = _(u"Not authorized to GET %(path)s") % {'path': location}
            raise NotAllowed(message)

        logger.info("...received; processing...")
        if updateCallback and updateCallback(msg=_(u"Processing: '%s'") % location):
            raise SharingError(_(u"Cancelled by user"))

        try:
            text = resp.body
            self.share.format.importProcess(text, item=self.share,
                changes=changes, previousView=previousView,
                updateCallback=updateCallback)

            # The share maintains bi-di-refs between Share and Item:
            for item in self.share.contents:
                self.share.items.append(item)

        except Exception, e:
            logging.exception(e)
            raise TransformationFailed(_(u"Transformation error: see chandler.log for more information"))

        lastModified = resp.headers.getHeader('Last-Modified')
        self.lastModified = lastModified[-1]
        logger.info("...imported, new last modified: %s" % self.lastModified)

        return stats

    def put(self):
        logger.info("'put( )' not support in SimpleHTTPConduit")

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

class OneTimeFileSystemShare(OneTimeShare):
    def __init__(self, path, itsName, formatclass, itsKind=None, itsView=None,
                 contents=None):

        conduit = FileSystemConduit(
            itsKind=itsKind, itsView=itsView, sharePath=path, shareName=itsName
        )
        format  = formatclass(itsView=itsView)
        super(OneTimeFileSystemShare, self).__init__(
            itsKind=itsKind, itsView=itsView,
            contents=contents, conduit=conduit, format=format
        )

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

def splitUrl(url):
    (scheme, host, path, query, fragment) = urlparse.urlsplit(url)

    if scheme == 'https':
        port = 443
        useSSL = True
    else:
        port = 80
        useSSL = False

    if host.find(':') != -1:
        (host, port) = host.split(':')
        port = int(port)

    return (useSSL, host, port, path, query, fragment)

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

def changedAttributes(item, fromVersion, toVersion):

    changes = set([])

    def historyCallback(i, version, status, values, references):
        if i is item:
            changes.update(values)
            changes.update(references)

    item.itsView.mapHistory(historyCallback, fromVersion, toVersion)

    return changes


def localChanges(view, fromVersion, toVersion):

    changedItems = {}

    def historyCallback(item, version, status, values, references):
        if changedItems.has_key(item.itsUUID):
            changes = changedItems[item.itsUUID]
        else:
            changes = set([])
            changedItems[item.itsUUID] = changes
        changes.update(values)
        changes.update(references)

    view.mapHistory(historyCallback, fromVersion, toVersion)

    return changedItems


def importValue(item, changes, attribute, value, previousView,
    updateCallback=None, setCallback=None):
    """
    Conditionally set a value (brought in via the sharing layer) on an item,
    depending on whether the new value is different than the old one, and
    whether the value has really changed remotely since the last sync.
    Conflicts are logged and are passed to the updateCallback, but remote
    changes win.  setCallback takes an item, an attribute name, and a value.
    """

    if isinstance(value, Item) or previousView is None:
        # For non-literals, just go ahead and set the new value; we don't
        # merge reference changes; if previousView is None, then we must
        # be trying to use view merging

        if setCallback is None:
            setattr(item, attribute, value)
        else:
            setCallback(item, attribute, value)
        return


    try:
        conflict = False
        attrType = item.getAttributeAspect(attribute, 'type')

        if type(value) in (str, unicode, int, float):
            needSerialized = False
        else:
            needSerialized = True
            (mimeType, encoding, curSerialized) = serializeLiteral(getattr(item,
                attribute, ""), attrType)
            (mimeType, encoding, newSerialized) = serializeLiteral(value,
                attrType)


        # First see if the new value equals the current value.  If it's the same
        # then we can skip the rest:

        if hasattr(item, attribute):
            if needSerialized:
                if curSerialized == newSerialized:
                    return
            else:
                currentValue = getattr(item, attribute)
                if currentValue == value:
                    return


        if changes and item.itsUUID in changes:
            modifiedAttributes = changes[item.itsUUID]
            if attribute in modifiedAttributes:

                # A potential conflict, but let's see if this wasn't really a
                # remote change.  What could have happened is the user changed
                # this attribute locally, but another user changed a different
                # attribute remotely.  We import the remote resource and start
                # assigning the attribute values, but we don't know from the server
                # which attributes were really modified remotely, just that at
                # least one attribute changed.  Here we can use the previousView
                # which is turned back in time to how things looked when we last
                # finished syncing.  We can compare this "new" value with how
                # things were back then.

                oldItem = previousView.findUUID(item.itsUUID)
                if oldItem is not None:
                    oldValue = getattr(oldItem, attribute, None)
                    # compare oldValue with value
                    if needSerialized:
                        (mimeType, encoding, oldSerialized) = \
                            serializeLiteral(oldValue, attrType)
                        if oldSerialized == newSerialized:
                            # there was no change to this value, ignore it
                            return
                    else:
                        if oldValue == value:
                            # there was no change to this value, ignore it
                            return

                    conflict = True


        if conflict:

            logger.warning("Sharing conflict: item '%s', attr '%s', "
                "local '%s', remote '%s'" %
                (item.getItemDisplayName().encode('ascii', 'replace'),
                attribute,
                getattr(item, attribute, None),
                value))

            if updateCallback:
                updateCallback(
                    msg=_(u"Conflict for item '%(name)s' "
                    "attribute: %(attribute)s '%(local)s' vs '%(remote)s'") %
                    (
                        {
                           'name' : item.getItemDisplayName(),
                           'attribute' : attribute,
                           'local' : getattr(item, attribute),
                           'remote' : value
                        }
                    )
                )
        else:

            logger.info("Sharing change: item '%s', attr '%s', value '%s'" % (item.getItemDisplayName().encode('ascii', 'replace'), attribute, value))


    except Exception, e:
        # To be safe, if anything goes wrong then simply continue on and set
        # the value (just as if importValue( ) weren't being used), logging
        # the exception:
        logger.exception(_(u"importValue failed"))


    # Currently, set the value regardless of conflict (server wins)
    if setCallback is None:
        setattr(item, attribute, value)
    else:
        setCallback(item, attribute, value)


def serializeLiteral(attrValue, attrType):

    mimeType = None
    encoding = None

    if isinstance(attrValue, Lob):
        mimeType = getattr(attrValue, 'mimetype', None)
        encoding = getattr(attrValue, 'encoding', None)
        data = attrValue.getInputStream().read()
        attrValue = base64.b64encode(data)

    if type(attrValue) is unicode:
        attrValue = attrValue.encode('utf-8')
    elif type(attrValue) is not str:
        attrValue = attrType.makeString(attrValue)

    return (mimeType, encoding, attrValue)



# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

def isShared(collection):
    """ Return whether an AbstractCollection has a Share item associated with it.

    @param collection: an AbstractCollection
    @type collection: AbstractCollection
    @return: True if collection does have a Share associated with it; False
        otherwise.
    """

    # See if any non-hidden shares are associated with the collection.
    # A "hidden" share is one that was not requested by the DetailView,
    # This is to support shares that don't participate in the whole
    # invitation process (such as transient import/export shares, or shares
    # for publishing an .ics file to a webdav server).

    for share in collection.shares:
        if share.hidden == False:
            return True
    return False

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

class SharingError(ChandlerException):
    pass


class AlreadyExists(SharingError):
    """
    Exception raised if a share already exists.
    """

class NotFound(SharingError):
    """
    Exception raised if a share/resource wasn't found.
    """

class NotAllowed(SharingError):
    """
    Exception raised if we don't have access.
    """

class Misconfigured(SharingError):
    """
    Exception raised if a share isn't properly configured.
    """

class CouldNotConnect(SharingError):
    """
    Exception raised if a conduit can't connect to an external entity
    due to DNS/network problems.
    """

class IllegalOperation(SharingError):
    """
    Exception raised if the entity a conduit is communicating with is
    denying an operation for some reason not covered by other exceptions.
    """

class TransformationFailed(SharingError):
    """
    Exception raised if import or export process failed.
    """

class AlreadySubscribed(SharingError):
    """
    Exception raised if subscribing to an already-subscribed url
    """

class VersionMismatch(SharingError):
    """
    Exception raised if syncing with a CloudXML share of an old version
    """

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

class WebDAVAccount(pim.ContentItem):
    schema.kindInfo(
        displayName=messages.ACCOUNT % {'accountName': 'WebDAV Account'},
        description="A WebDAV 'Account'\n\n"
            "Issues:\n"
            "   Long term we're probably not going to treat WebDAV as an "
            "account, but rather how a web browser maintains URL-to-ACL "
            "mappings.\n",
    )
    username = schema.One(
        schema.Text, displayName = messages.USERNAME, initialValue = u'',
    )
    password = schema.One(
        schema.Text,
        displayName = messages.PASSWORD,
        description = 
            'Issues: This should not be a simple string. We need some solution for '
            'encrypting it.\n',
        initialValue = u'',
    )
    host = schema.One(
        schema.Text,
        displayName = messages.HOST,
        doc = 'The hostname of the account',
        initialValue = u'',
    )
    path = schema.One(
        schema.Text,
        displayName = messages.PATH,
        doc = 'Base path on the host to use for publishing',
        initialValue = u'',
    )
    port = schema.One(
        schema.Integer,
        displayName = messages.PORT,
        doc = 'The non-SSL port number to use',
        initialValue = 80,
    )
    useSSL = schema.One(
        schema.Boolean,
        displayName = _(u'Use secure connection (SSL/TLS)'),
        doc = 'Whether or not to use SSL/TLS',
        initialValue = False,
    )
    accountType = schema.One(
        displayName = _(u'Account Type'), initialValue = 'WebDAV',
    )
    conduits = schema.Sequence(WebDAVConduit, inverse = WebDAVConduit.account)

    def getLocation(self):
        """
        Return the base url of the account
        """

        if self.useSSL:
            scheme = "https"
            defaultPort = 443
        else:
            scheme = "http"
            defaultPort = 80

        if self.port == defaultPort:
            url = "%s://%s" % (scheme, self.host)
        else:
            url = "%s://%s:%d" % (scheme, self.host, self.port)

        sharePath = self.path.strip("/")
        url = urlparse.urljoin(url, sharePath + "/")
        return url

    @classmethod
    def findMatchingAccount(cls, view, url):
        """
        Find a WebDAV account which corresponds to a URL.

        The url being passed in is for a collection -- it will include the
        collection name in the url.  We need to find a webdav account who
        has been set up to operate on the parent directory of this collection.
        For example, if the url is http://pilikia.osafoundation.org/dev1/foo/
        we need to find an account whose schema+host+port match and whose path
        starts with /dev1

        Note: this logic assumes only one account will match; you aren't
        currently allowed to have to multiple webdav accounts pointing to the
        same scheme+host+port+path combination.

        @param view: The repository view object
        @type view: L{repository.persistence.RepositoryView}
        @param url: The url which points to a collection
        @type url: String
        @return: An account item, or None if no WebDAV account could be found.
        """

        (useSSL, host, port, path, query, fragment) = splitUrl(url)

        # Get the parent directory of the given path:
        # '/dev1/foo/bar' becomes ['dev1', 'foo']
        path = path.strip('/').split('/')[:-1]
        # ['dev1', 'foo'] becomes "dev1/foo"
        path = "/".join(path)

        for account in cls.iterItems(view):
            # Does this account's url info match?
            accountPath = account.path.strip('/')
            if account.useSSL == useSSL and account.host == host and \
               account.port == port and path.startswith(accountPath):
                return account

        return None


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

class ImportExportFormat(pim.ContentItem):

    schema.kindInfo(displayName=u"Import/Export Format Kind")

    share = schema.One(Share, inverse = Share.format)

    STYLE_SINGLE = 'single' # Share represented by monolithic file
    STYLE_DIRECTORY = 'directory' # Share is a directory where each item has
                                  # its own file

    def fileStyle(self):
        """
        Should return 'single' or 'directory'
        """
        pass

    def shareItemPath(self):
        """
        Return the path for the file representing the Share item
        """
        return None # None indicates there is no file representing the Share
                    # item

    def contentType(self, item):
        return "text/plain"

    def acceptsItem(self, item):
        return True


class CloudXMLFormat(ImportExportFormat):

    schema.kindInfo(displayName=u"Cloud XML Import/Export Format Kind")

    cloudAlias = schema.One(schema.Text, initialValue='sharing')

    def fileStyle(self):
        return self.STYLE_DIRECTORY

    def extension(self, item):
        return "xml"

    def shareItemPath(self):
        return "share.xml"

    def importProcess(self, text, extension=None, item=None, changes=None,
        previousView=None, updateCallback=None):
        doc = libxml2.parseDoc(text)
        node = doc.children
        try:

            # @@@MOR Disabling the use of queued notifications, as it is
            # not needed at the moment.  Leaving it in (commented out) in
            # case the need arises.

            # self.itsView.recordChangeNotifications()

            item = self._importNode(node, item=item, changes=changes,
                previousView=previousView, updateCallback=updateCallback)

        finally:

            # self.itsView.playChangeNotifications()

            doc.freeDoc()

        return item



    def exportProcess(self, item, depth=0, items=None):

        if items is None:
            items = {}

        if depth == 0:
            result = '<?xml version="1.0" encoding="UTF-8"?>\n\n'
            versionString = "version='%s' " % CLOUD_XML_VERSION
        else:
            result = ''
            versionString = ''

        # Collect the set of attributes that are used in this format
        attributes = self.share.getSharedAttributes(item)

        indent = "   "

        if items.has_key(item.itsUUID):
            result += indent * depth
            result += "<%s uuid='%s' />\n" % (item.itsKind.itsName,
                                               item.itsUUID)
            return result

        items[item.itsUUID] = 1

        result += indent * depth

        if item.itsKind.isMixin():
            classNames = []
            for kind in item.itsKind.superKinds:
                klass = kind.classes['python']
                className = "%s.%s" % (klass.__module__, klass.__name__)
                classNames.append(className)
            classes = ",".join(classNames)
        else:
            klass = item.itsKind.classes['python']
            classes = "%s.%s" % (klass.__module__, klass.__name__)

        result += "<%s %sclass='%s' uuid='%s'>\n" % (item.itsKind.itsName,
                                                    versionString,
                                                    classes,
                                                    item.itsUUID)

        depth += 1

        for attrName in attributes:

            if not hasattr(item, attrName):
                continue

            attrValue = item.getAttributeValue(attrName)
            if attrValue is None:
                continue


            otherName = item.itsKind.getOtherName(attrName, item, None)
            cardinality = item.getAttributeAspect(attrName, 'cardinality')
            attrType = item.getAttributeAspect(attrName, 'type')

            result += indent * depth

            if otherName: # it's a bidiref
                result += "<%s>\n" % attrName

                if cardinality == 'single':
                    if attrValue is not None:
                        result += self.exportProcess(attrValue, depth+1, items)

                elif cardinality == 'list':
                    for value in attrValue:
                        result += self.exportProcess(value, depth+1, items)

                elif cardinality == 'dict':
                    # @@@MOR
                    pass

                result += indent * depth

            else: # it's a literal (@@@MOR could be SingleRef though)

                result += "<%s" % attrName

                if cardinality == 'single':

                    if isinstance(attrValue, Item):
                        result += ">\n"
                        result += self.exportProcess(attrValue, depth+1, items)
                    else:
                        (mimeType, encoding, attrValue) = \
                            serializeLiteral(attrValue, attrType)
                        attrValue = attrValue.replace('&', '&amp;')
                        attrValue = attrValue.replace('<', '&lt;')
                        attrValue = attrValue.replace('>', '&gt;')

                        if mimeType:
                            result += " mimetype='%s'" % mimeType

                        if encoding:
                            result += " encoding='%s'" % encoding

                        result += ">"
                        result += attrValue


                elif cardinality == 'list':
                    result += ">"
                    depth += 1
                    result += "\n"

                    for value in attrValue:
                        result += indent * depth
                        result += "<value"

                        (mimeType, encoding, value) = \
                            serializeLiteral(value, attrType)
                        value = value.replace('&', '&amp;')
                        value = value.replace('<', '&lt;')
                        value = value.replace('>', '&gt;')

                        if mimeType:
                            result += " mimetype='%s'" % mimeType

                        if encoding:
                            result += " encoding='%s'" % encoding

                        result += ">"
                        result += value
                        result += "</value>\n"

                    depth -= 1

                    result += indent * depth

                elif cardinality == 'dict':
                    result += ">"
                    # @@@MOR
                    pass

            result += "</%s>\n" % attrName

        depth -= 1
        result += indent * depth
        result += "</%s>\n" % item.itsKind.itsName
        return result


    def _getNode(self, node, attribute):

        # @@@MOR This method only supports traversal of single-cardinality
        # attributes

        # attribute can be a dot-separated chain of attribute names
        chain = attribute.split(".")
        attribute = chain[0]
        remaining = chain[1:]

        child = node.children
        while child:
            if child.type == "element":
                if child.name == attribute:
                    if not remaining:
                        # we're at the end of the chain
                        return child
                    else:
                        # we need to recurse. @@@MOR for now, not supporting
                        # list
                        grandChild = child.children
                        while grandChild.type != "element":
                            # skip over non-elements
                            grandChild = grandChild.next
                        return self._getNode(grandChild,
                         ".".join(remaining))

            child = child.next
        return None


    def _importNode(self, node, item=None, changes=None,
        previousView=None, updateCallback=None):

        view = self.itsView
        kind = None
        kinds = []

        versionNode = node.hasProp('version')
        if versionNode:
            versionString = versionNode.content
            if versionString != CLOUD_XML_VERSION:
                raise VersionMismatch(_(u"Incompatible share"))

        if item is None:

            uuidNode = node.hasProp('uuid')
            if uuidNode:
                try:
                    uuid = UUID(uuidNode.content)
                    item = self.itsView.findUUID(uuid)
                except Exception, e:
                    logger.exception("Problem processing uuid %s" % uuid)
                    return item
            else:
                uuid = None


        classNode = node.hasProp('class')
        if classNode:
            classNameList = classNode.content.split(",")
            for classPath in classNameList:
                try:
                    klass = schema.importString(classPath)
                    kind = klass.getKind(view)
                    if kind is not None:
                        kinds.append(kind)
                except ImportError:
                    pass
        else:
            # No kind means we're simply looking up an item by uuid and
            # returning it
            return item

        if len(kinds) == 0:
            # we don't have any of the kinds provided
            logger.info("No kinds found locally for %s" % classNameList)
            return None
        elif len(kinds) == 1:
            kind = kinds[0]
        else: # time to mixin
            kind = kinds[0].mixin(kinds[1:])

        if item is None:
            # item search turned up empty, so create an item...
            if uuid:
                parent = self.findPath("//userdata")
                item = kind.instantiateItem(None, parent, uuid,
                                            withInitialValues=True)
            else:
                item = kind.newItem(None, None)

        else:
            # there is a chance that the incoming kind is different than the
            # item's kind
            item.itsKind = kind

        # we have an item, now set attributes

        # Set a temporary attribute that items can check to see if they're in
        # the middle of being imported:
        item._share_importing = True

        try:
            attributes = self.share.getSharedAttributes(item)
            for attrName in attributes:

                attrNode = self._getNode(node, attrName)
                if attrNode is None:
                    if item.hasLocalAttributeValue(attrName):
                        item.removeAttributeValue(attrName)
                    continue

                otherName = item.itsKind.getOtherName(attrName, item, None)
                cardinality = item.getAttributeAspect(attrName, 'cardinality')
                attrType = item.getAttributeAspect(attrName, 'type')

                # This code depends on attributes having their type set, which
                # might not always be the case. What should be done is to encode
                # the value type into the shared xml itself:

                if otherName or (isinstance(attrType, Item) and \
                    not isinstance(attrType, Type)): # it's a ref

                    if cardinality == 'single':
                        valueNode = attrNode.children
                        while valueNode and valueNode.type != "element":
                            # skip over non-elements
                            valueNode = valueNode.next
                        if valueNode:
                            valueItem = self._importNode(valueNode,
                                changes=changes, previousView=previousView,
                                updateCallback=updateCallback)
                            if valueItem is not None:
                                setattr(item, attrName, valueItem)

                    elif cardinality == 'list':
                        valueNode = attrNode.children
                        while valueNode:
                            if valueNode.type == "element":
                                valueItem = self._importNode(valueNode,
                                    changes=changes,
                                    previousView=previousView,
                                    updateCallback=updateCallback)
                                if valueItem is not None:
                                    item.addValue(attrName, valueItem)

                            valueNode = valueNode.next

                    elif cardinality == 'dict':
                        pass

                else: # it's a literal

                    if cardinality == 'single':

                        mimeTypeNode = attrNode.hasProp('mimetype')

                        if mimeTypeNode: # Lob
                            mimeType = mimeTypeNode.content
                            indexed = mimeType == "text/plain"
                            value = base64.b64decode(attrNode.content)
                            value = utils.dataToBinary(item, attrName, value,
                                mimeType=mimeType, indexed=indexed)

                            encodingNode = attrNode.hasProp('encoding')
                            if encodingNode:
                                value.encoding = encodingNode.content

                        else:
                            content = attrNode.content
                            content = unicode(content, 'utf-8')
                            value = attrType.makeValue(content)


                        importValue(item, changes, attrName,
                            value, previousView=previousView,
                            updateCallback=updateCallback)


                    elif cardinality == 'list':

                        values = []
                        valueNode = attrNode.children
                        while valueNode:
                            if valueNode.type == "element":

                                mimeTypeNode = valueNode.hasProp('mimetype')

                                if mimeTypeNode: # Lob
                                    mimeType = mimeTypeNode.content
                                    indexed = mimeType == "text/plain"
                                    value = base64.b64decode(attrNode.content)
                                    value = utils.dataToBinary(item, attrName,
                                        value, mimeType=mimeType,
                                        indexed=indexed)

                                    encodingNode = valueNode.hasProp('encoding')
                                    if encodingNode:
                                        value.encoding = encodingNode.content

                                else:
                                    content = valueNode.content
                                    content = unicode(content, 'utf-8')
                                    value = attrType.makeValue(content)


                                values.append(value)
                            valueNode = valueNode.next

                        logger.debug("for %s setting %s to %s" % \
                            (item.getItemDisplayName().encode('ascii',
                            'replace'), attrName, values))
                        setattr(item, attrName, values)

                    elif cardinality == 'dict':
                        pass

        finally:
            del item._share_importing

        return item


