__revision__  = "$Revision$"
__date__      = "$Date$"
__copyright__ = "Copyright (c) 2004 Open Source Applications Foundation"
__license__   = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

import repository.item.Item as Item
import application.Globals as Globals

"""
 * Need to dirty the collection when the rule attribute is changed
 * Need to figure out what remove() should actually do
 * Is it possible to remove include/exclude all together and replace them
   with append and remove?
"""

class ItemCollection(Item.Item):
    def __init__(self, name=None, parent=None, kind=None):
        if not parent:
            parent = Globals.repository.findPath('//userdata/contentitems')
        super(ItemCollection, self).__init__(name, parent, kind)

        # our result cache
        self.results = []

        self.onItemLoad()

    def onItemLoad(self):
        # subscribe to query_changed notifications incase our query changes
        events = [Globals.repository.findPath('//parcels/osaf/framework/query_changed')]
        Globals.notificationManager.Subscribe(events, id(self), self._queryChangedCallback)

        # refresh the result cache
        self.__refresh()

    def onItemUnload(self):
        Globals.notificationManager.Unsubscribe(id(self))

    def _queryChangedCallback(self, notification):
        # if the query that changed is ours, we must refresh our result cache
        if self.rule:
            if notification.data['query'] == self.rule.itsUUID:
                self.__refresh()


    # python container functions
    def __nonzero__(self):
        return True

    def __len__(self):
        return len(self.results)

    def __iter__(self):
        repository = self.getRepositoryView()
        results = self.results
        for uuid in results:
            yield repository[uuid]

    def __contains__(self, item):
        return item.itsUUID in self.results

    def __getitem__(self, index):
        return self.getRepositoryView()[self.results[index]]

    def index(self, item):
        return self.results.index(item.itsUUID)

    def remove(self, item):
        # need to define what it really means to remove an item
        raise NotImplementedError


    # Inclusion and Exclusion APIs
    def include(self, item):
        uuid = item.itsUUID

        # don't add ourselves more than once
        if uuid in self.inclusions:
            return
        
        self.inclusions.append(uuid)

        # if the item we're including was already excluded, remove it
        # from that list
        if uuid in self.exclusions:
            self.exclusions.remove(uuid)

        if uuid not in self.results:
            self.results.append(uuid)
            self.__dirty()

    def removeInclusion(self, item):
        uuid = item.itsUUID
        self.inclusions.remove(uuid)

        self.results.remove(uuid)
        self.__dirty()

    def exclude(self, item):
        uuid = item.itsUUID

        # don't add ourselves more than once
        if uuid in self.exclusions:
            return

        self.exclusions.append(uuid)

        # if the item we're excluded was already included, remove it
        # from that list
        if uuid in self.inclusions:
            self.inclusions.remove(uuid)

        if uuid in self.results:
            self.results.remove(uuid)
            self.__dirty()

    def removeExclusion(self, item):
        self.exclusions.remove(item.itsUUID)
        self.__refresh()


    # result cache building
    def __refresh(self):
        results = []

        inclusions = self.inclusions
        exclusions = self.exclusions
        rule = self.rule
        if not rule:
            rule = []

        for item in rule:
            uuid = item.itsUUID
            if uuid not in exclusions:
                results.append(uuid)

        for uuid in inclusions:
            if uuid not in exclusions:
                if uuid not in results: # keep duplicates out
                    results.append(uuid)

        self.results = results

        self.__dirty()

    def __dirty(self):
        # post collection_changed notification
        self.getRepositoryView().findPath('//parcels/osaf/contentmodel/collection_changed').Post( {'collection' : self.itsUUID} )



class NamedCollection(ItemCollection):
    def __init__(self, name=None, parent=None, kind=None):
        if not kind:
            kind = Globals.repository.findPath('//parcels/osaf/contentmodel/NamedCollection')
        super(NamedCollection, self).__init__(name, parent, kind)

class AdHocCollection(ItemCollection):
    def __init__(self, name=None, parent=None, kind=None):
        if not kind:
            kind = Globals.repository.findPath('//parcels/osaf/contentmodel/AdHocCollection')
        super(NamedCollection, self).__init__(name, parent, kind)
        
class EphemeralCollection(ItemCollection):
    def __init__(self, name=None, parent=None, kind=None):
        if not kind:
            kind = Globals.repository.findPath('//parcels/osaf/contentmodel/EphemeralCollection')
        super(NamedCollection, self).__init__(name, parent, kind)

