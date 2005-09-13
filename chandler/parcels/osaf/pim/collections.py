_date__ = "$Date: 2005-07-08 00:29:48Z $"
__copyright__ = "Copyright (c) 2003-2004 Open Source Applications Foundation"
__license__ = "http://osafoundation.org/Chandler_0.1_license_terms.htm"
__parcel__ = "osaf.pim"

from application import schema
from repository.item.Sets import Set, MultiUnion, Union, MultiIntersection, Intersection, Difference, KindSet, FilteredSet
from repository.item.Item import Item
from chandlerdb.item.ItemError import NoSuchIndexError
from osaf.pim import items
import logging, os, re

logger = logging.getLogger(__name__)

def mapChangesCallable(item, version, status, literals, references):
    """
    Pick up changes to items in C{ListCollections} and C{KindCollections}. 

    These changes are then passed along to the contentsUpdated method
    of any collection containing the modified items. 

    This is a callback for
    C{repository.persistence.DBRepositoryView.mapChanges}
    
    c{mapChangesCallable} is called from the application's idle loop:
    C{application.Application.wxApplication.OnIdle}
    """
    # handle changes to items in a ListCollection
    if hasattr(item,'collections'):
        for i in item.collections:
            i.contentsUpdated(item)

    # handle changes to items in an existing KindCollection
    # is the item in a kind collection?
    try:
        #@@@ this is not the most efficient way...
        # Find the global directory of kind collections
        kc = schema.ns("osaf.pim.collections", item.itsView).kind_collections
        for i in kc.collections:
            if item in i:
                i.contentsUpdated (item)
    except AttributeError, ae:
        #logger.debug(ae)
        # @@@ intentionally swallow AttributeErrors from parcel loading
        # due to notification attempts before reps are created.
        pass 


class AbstractCollection(items.ContentItem):
    """
    The base class for all Collection types.

    Collections are items and provide an API for client to subscribe
    to their notifications.

    The general usage paradigm for collections is to instantiate a collection
    and then set the values of attributes as necessary (instead of during
    construction)
    """
    schema.kindInfo(
        displayName="AbstractCollection"
    )

    # the repository set underlying the Collection
    rep = schema.One(schema.TypeReference('//Schema/Core/AbstractSet'))
    # the set of subscribers 
    subscribers = schema.Many(initialValue=set())
    # collectionEventHandler is used when a collection subscribes to
    # the results of another collection.
    collectionEventHandler = schema.One(schema.String, initialValue="collectionChanged")
    # the name of the default index
    indexName   = schema.One(schema.String, initialValue="__adhoc__")


    """
      The following collection attributes may be moved once the dust
    settles on pje's external attribute mechanism
    """
    renameable              = schema.One(schema.Boolean)
    color                   = schema.One(schema.Anything)
    iconName                = schema.One(schema.String)
    iconNameHasKindVariant  = schema.One(schema.Boolean, defaultValue = False)
    colorizeIcon            = schema.One(schema.Boolean, defaultValue = True)
    dontDisplayAsCalendar   = schema.One(schema.Boolean, defaultValue = False)
    """
      A dictionary mapping a KindName string to a new displayName.
    """
    displayNameAlternatives = schema.Mapping (schema.String)

    collectionList = schema.Sequence(
        'AbstractCollection',
        doc="Views, e.g. the Calendar, that display collections need to know "
            "which collection are combined to make up the calendar. collectionList"
            "is an optional parameter for this purpose.",
        defaultValue = []
    )

    invitees = schema.Sequence(
        "osaf.pim.mail.EmailAddress",
        doc="The people who are being invited to share in this item; filled "
            "in when the user types in the DV's 'invite' box, then cleared on "
            "send (entries copied to the share object).\n\n"
            "Issue: Bad that we have just one of these per item collection, "
            "though an item collection could have multiple shares post-0.5",
        inverse="inviteeOf",
        initialValue=()
    )   

    # redirections 
    about = schema.Role(redirectTo="displayName")

    schema.addClouds(
        copying = schema.Cloud(
            invitees,
            byRef=['contentsOwner']
        ),
        sharing = schema.Cloud( none = ["displayName"] ),
    )

    def collectionChanged(self, op, item, name, other, *args):
        """
        The method called by the repository level set that backs a collection.

        C{collectionChanged} dispatches to C{notifySubscribers} which does the
        work of delivering notifications to all subscribers.
        """
        # mapChanges (called in the idle loop)
        # propagates any updates (not add/removes) that
        # happened since the last
        self.notifySubscribers(op, item, name, other, *args)

    def notifySubscribers(self, op, item, name, other, *args):
        """
        Deliver notifications to all subscribers

        Calls the method named in each subscribers' C{collectionEventHandler}
        to deliver the notification.  If the item has no
        C{collectionEventEventHandler}, C{onCollectionEvent} will be called
        if it exists.
        """
        for i in self.subscribers:
            method_name = getattr(i, "collectionEventHandler", "onCollectionEvent")
            if method_name != None:
                method = getattr(type(i), method_name, None)
                if method != None:
                    method(i, op, item, name, other, *args)
                else:
                    logger.debug("Didn't find the specified notification handler named %s" % (method_name))
            else:
                logger.debug("notification handler not specfied - no collectionEventHandler attribute")

    def contentsUpdated(self, item):
        """
        Callback for handling changes found by C{mapChangesCallable}
        """
        pass

    def __contains__(self, item):
        return self.rep.__contains__(item)

    def __iter__(self):
        for i in self.rep:
            yield i

    def __len__(self):
        try:
            return len(self.rep)
        except ValueError:
            self.createIndex()
            return len(self.rep)

    def createIndex (self):
        """
        Create an index on this collection

        If the C{{indexName} attribute of this collection is set to
        "__adhoc__" then a numeric index will be created.  Otherwise
        the C{indexName} attribute should contain the name of the
        attribute (of an item) to be indexed.
        """
        if self.indexName == "__adhoc__":
            self.rep.addIndex (self.indexName, 'numeric')
        else:
            self.rep.addIndex (self.indexName, 'attribute', attribute=self.indexName)

    def __getitem__ (self, index):
        """
        Support indexing using []
        """

        try:
            return self.rep.getByIndex (self.indexName, index)
        except NoSuchIndexError:
            self.createIndex()
            return self.rep.getByIndex (self.indexName, index)

    def index (self, item):
        """
        Return the position of item in the index.
        """
        try:
            return self.rep.getIndexPosition (self.indexName, item)
        except NoSuchIndexError:
            self.createIndex()
            return self.resultSet.getIndexPosition (self.indexName, item)

    def __nonzero__(self):
        return True

class KindCollection(AbstractCollection):
    """
    A Collection of all of the items of a particular kind

    The C{kind} attribute to the C{Kind} determines the C{Kind} of the items
    in the C{KindCollection}

    The C{recursive} attribute determines whether items of subkinds are
    included (C{True}) in the C{KindCollection}
    """
    schema.kindInfo(
        displayName="KindCollection"
    )

    kind = schema.One(schema.TypeReference('//Schema/Core/Kind'), initialValue=None)
    recursive = schema.One(schema.Boolean, initialValue=False)
    # the KindCollectionDirectory is a data structure the records all
    # the KindCollections in the system, for use by mapChangesCallable
    directory = schema.One("KindCollectionDirectory", initialValue=None)

    def __init__(self, *args, **kw):
        super(KindCollection, self).__init__(*args, **kw)
        # find the global KindCollectionDirectory item.
        kc = schema.ns("osaf.pim.collections", self.itsView).kind_collections
        kc.collections.add(self)
    
    def contentsUpdated(self, item):
        self.rep.notify('changed', item)

    def onValueChanged(self, name):
        if name == "kind" or name == "recursive":
            self.rep = KindSet(self.kind, self.recursive)

class KindCollectionDirectory(schema.Item):
    """
    Directory of all KindCollections in Chandler
    """
    # just a ref collection, really
    collections = schema.Sequence(
        "KindCollection",
        inverse = KindCollection.directory,
        doc="all KindCollections - intended to be a singleton.  Use to propagate change notifications", initialValue=[])

def installParcel(parcel, old_version = None):
    """
    Parcel install time hook
    """
    # create the global KindCollectionDirectory item.
    KindCollectionDirectory.update(parcel, "kind_collections")

class ListCollection(AbstractCollection):
    """
    A collection that contains only those items that are explicitly added to it.

    Backed by a ref-collection
    """
    schema.kindInfo(
        displayName="ListCollection"
    )

    refCollection = schema.Sequence(otherName='collections',initialValue=[])

    trashFor = schema.Many('InclusionExclusionCollection', otherName='trash', initialValue=[])

    def __init__(self, *args, **kw):
        super(ListCollection, self).__init__(*args, **kw)
        self.rep = Set((self,'refCollection'))

    def add(self, item):
        self.refCollection.add(item)

    def clear(self):
        self.refCollection.clear()

    def first(self):
        self.refCollection.first()

    def remove(self, item):
        self.refCollection.remove(item)

    def contentsUpdated(self, item):
        self.rep.notify('changed', item)

    def empty(self):
        for item in self:
            item.delete(True)

class DifferenceCollection(AbstractCollection):
    """
    A collection containing the set theoretic difference of two collections

    Assign the C{sources} attribute (a list) with the collections to be
    differenced
    """
    schema.kindInfo(
        displayName="DifferenceCollection"
    )

    sources = schema.Sequence(AbstractCollection, initialValue=[])

    schema.addClouds(
        copying = schema.Cloud(byCloud=[sources]),
    )

    def onValueChanged(self, name):
        if name == "sources":
            if self.sources != None:
                assert len(self.sources) <= 2, "DifferenceCollection can only handle 2 sources"

                if len(self.sources) == 2:
                    self.rep = Difference((self.sources[0], "rep"),(self.sources[1], "rep"))
                    self.subscribers.clear()
                    for i in self.sources:
                        i.subscribers.add(self)

class UnionCollection(AbstractCollection):
    """
    A collection containing the set theoretic union of at least 2 collections

    Assign the C{sources} attribute (a list) with the collections to be
    unioned
    """
    schema.kindInfo(
        displayName="UnionCollection"
    )

    sources = schema.Sequence(AbstractCollection, initialValue=[])

    schema.addClouds(
        copying = schema.Cloud(byCloud=[sources]),
    )

    def onValueChanged(self, name):
        if name == "sources":
            if self.sources != None and len(self.sources)> 1:
                # optimize for the binary case
                if len(self.sources) == 2:
                    self.rep = Union((self.sources[0],"rep"),(self.sources[1],"rep"))
                else:
                    self.rep = MultiUnion(*[(i, "rep") for i in self.sources])
                self.subscribers.clear()
                for i in self.sources:
                    i.subscribers.add(self)



class IntersectionCollection(AbstractCollection):
    """
    A collection containing the set theoretic intersection of at least 2 collections

    Assign the C{sources} attribute (a list) with the collections to be
    intersected
    """
    schema.kindInfo(
        displayName="IntersectionCollection"
    )

    sources = schema.Sequence(AbstractCollection, initialValue=[])

    schema.addClouds(
        copying = schema.Cloud(byCloud=[sources]),
    )

    def onValueChanged(self, name):
        if name == "sources":
            if self.sources != None and len(self.sources) > 1:
                # optimize for the binary case
                if len(self.sources) == 2:
                    self.rep = Intersection((self.sources[0],"rep"),(self.sources[1],"rep"))
                else:
                    self.rep = MultiIntersection(*[(i, "rep") for i in self.sources])
            self.subscribers.clear()
            for i in self.sources:
                i.subscribers.add(self)

# regular expression for finding the attribute name used by
# hasLocalAttributeValue
delPat = re.compile(".*hasLocalAttributeValue\(([^\)]*)\).*")

class FilteredCollection(AbstractCollection):
    """
    A collection which is the result of applying a boolean predicate
    to every item of another collection
    
    Assign the C{source} attribute to specify the collection to be filtered

    Assign the C{filterExpression} attribute with a string containing
    a Python expression.  If the expression returns C{True} for an
    item in the C{source} it will be in the FilteredCollection.

    Assign the C{filterAttributes} attribute with a list of attribute
    names (Strings), which are accessed by the C{filterExpression}.
    Failure to provide this list will result in missing notifications
    """
    schema.kindInfo(
        displayName="FilteredCollection"
    )

    source = schema.One(AbstractCollection, initialValue=None)
    filterExpression = schema.One(schema.String, initialValue="")
    filterAttributes = schema.Sequence(schema.String, initialValue=[])

    schema.addClouds(
        copying = schema.Cloud(byCloud=[source]),
    )


    def onValueChanged(self, name):
        if name == "source" or name == "filterExpression" or name =="filterAttributes":
            if self.source != None:
                try:
                    if self.filterExpression != "" and self.filterAttributes != []:

                        # see if the expression contains hasLocalAttributeValue
                        m = delPat.match(self.filterExpression)
                        if m:
                            delatt = m.group(1)
                            if delatt is not None:
                                # strip leading quotes
                                if delatt.startswith("'") or delatt.startswith('"'):
                                    delatt = delatt[1:-1] 
                                delatt = [ delatt.replace("item.","") ]
                        else:
                            delatt = []
                        attrTuples = []

                        # build a list of (item, monitor-operation) tuples
                        for i in self.filterAttributes:
                            attrTuples.append((i, "set"))
                            for j in delatt:
                                attrTuples.append((j, "remove"))

                        self.rep = FilteredSet((self.source, "rep"), self.filterExpression, attrTuples)
                    self.subscribers.clear()
                    for i in self.sources:
                        i.subscribers.add(self)
                except AttributeError, ae:
                    pass


class InclusionExclusionCollection(DifferenceCollection):
    """
    InclusionExclusionCollections implement inclusions, exclusions, source,
    and trash along with methods for add and remove
    """

    inclusions = schema.One(AbstractCollection)
    exclusions = schema.One(AbstractCollection)
    trash = schema.One(ListCollection, otherName='trashFor', initialValue=None)

    def add (self, item):
        """
          Add an item to the collection
        """

        logger.debug("Adding %s to %s...",
            item.getItemDisplayName(), self.getItemDisplayName())

        if item not in self.inclusions:
            logger.debug("...adding to inclusions (%s)",
                self.inclusions.getItemDisplayName())
            self.inclusions.add (item)

        if item in self.exclusions:
            logger.debug("...removing from exclusions (%s)",
                self.exclusions.getItemDisplayName())
            self.exclusions.remove (item)

        # If a trash is associated with this collection, remove the item
        # from the trash.  This has the additional benefit of having the item
        # reappear in any collection which has the item in its inclusions

        if self.trash is not None and item in self.trash:
            logger.debug("...removing from trash (%s)",
                self.trash.getItemDisplayName())
            self.trash.remove (item)

        logger.debug("...done adding %s to %s",
            item.getItemDisplayName(), self.getItemDisplayName())

    def remove (self, item):
        """
          Remove an item from the collection
        """

        logger.debug("Removing %s from %s...",
            item.getItemDisplayName(), self.getItemDisplayName())

        if item not in self.exclusions:
            logger.debug("...adding to exclusions (%s)",
                self.exclusions.getItemDisplayName())
            self.exclusions.add (item)

        if item in self.inclusions:
            logger.debug("...removing from inclusions (%s)",
                self.inclusions.getItemDisplayName())
            self.inclusions.remove (item)

        # If this item is not in any of the collections that share our trash,
        # add the item to the trash
        if self.trash is not None:
            found = False
            for collection in self.trash.trashFor:
                if item in collection:
                    found = True
                    break
            if not found:
                logger.debug("...adding to trash (%s)",
                    self.trash.getItemDisplayName())
                self.trash.add(item)

        logger.debug("...done removing %s from %s",
            item.getItemDisplayName(), self.getItemDisplayName())


    def setup(self, source=None, exclusions=None, trash=None):
        """
            Auto-configure the source tree depending on the arguments provided.
        """

        # An inclusions ListCollection is always created.  if source is
        # provided, then an additional UnionCollection is created to combine
        # source and inclusions

        if source is None:
            innerSource = ListCollection(parent=self)
            self.inclusions = innerSource
        else:
            innerSource = UnionCollection(parent=self)
            innerSource.sources = [source, ListCollection(parent=self)]
            self.inclusions = innerSource.sources[1]


        # Typically we will create an exclusions ListCollection; however,
        # a collection like 'All' will instead want to use the Trash collection
        # for exclusions

        if exclusions is None:
            exclusions = ListCollection(parent=self)
        self.exclusions = exclusions

        # You can designate a certain ListCollection to be used for this
        # collection's trash; in this case, an additional DifferenceCollection
        # will be created to remove any trash items from this collection. Any
        # collections which share a trash get the following benefits:
        # - Adding an item to the trash will make the item disappear from
        #   collections sharing that trash collection
        # - When an item is removed from a collection, it will automatically
        #   be moved to the trash if it doesn't appear in any collection which
        #   shares that trash

        if trash is not None:
            outerSource = DifferenceCollection(parent=self)
            outerSource.sources = [innerSource, trash]
        else:
            outerSource = innerSource
            trash = exclusions
        self.trash = trash

        self.sources = [outerSource, exclusions]

        return self
