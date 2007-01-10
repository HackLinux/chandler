#   Copyright (c) 2003-2006 Open Source Applications Foundation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


from chandlerdb.util.c import Nil
from chandlerdb.item.c import isitem, isitemref
from chandlerdb.item.ItemError import ReadOnlyAttributeError, OwnedValueError
from chandlerdb.item.ItemValue import ItemValue


class PersistentCollection(ItemValue):
    """
    A persistence aware collection, tracking changes into a dirty bit.

    This class is abstract and is to be used together with a concrete
    collection class such as list or dict.
    """

    def __init__(self, item=None, attribute=None):

        super(PersistentCollection, self).__init__(item, attribute)
        self._readOnly = False

    def setReadOnly(self, readOnly=True):

        self._readOnly = readOnly

    def isReadOnly(self):

        return self._readOnly

    def _setOwner(self, item, attribute):

        oldItem, oldAttribute = super(PersistentCollection, self)._setOwner(item, attribute)

        if oldItem is not item or oldAttribute is not attribute:
            for value in self._itervalues():
                if isinstance(value, ItemValue):
                    value._setOwner(item, attribute)

    @classmethod
    def prepareValue(cls, item, attribute, value, setDirty=True):
        
        if isinstance(value, ItemValue):
            if value._owner is not Nil:
                value = value._copy(item, attribute, 'copy')
            else:
                value._setOwner(item, attribute)
        elif isinstance(value, list):
            value = PersistentList(item, attribute, value, setDirty)
        elif isinstance(value, dict):
            value = PersistentDict(item, attribute, value, setDirty)
        elif isinstance(value, tuple):
            value = PersistentTuple(item, attribute, value, setDirty)
        elif isinstance(value, set):
            value = PersistentSet(item, attribute, value, setDirty)
        elif isitem(value):
            value = value.itsRef

        return value

    def _restoreValue(self, value):

        if self._owner is not Nil and isitemref(value):
            return value(True)

        return value

    def _useValue(self, value):

        if isinstance(value, PersistentCollection):
            return value
        if isitemref(value):
            return value

        if isitem(value):
            return value.itsRef
        elif isinstance(value, list):
            return [self._useValue(v) for v in value]
        elif isinstance(value, set):
            return set([self._useValue(v) for v in value])
        elif isinstance(value, tuple):
            return tuple([self._useValue(v) for v in value])
        elif isinstance(value, dict):
            d = {}
            for k, v in value.itervalues():
                d[k] = self._useValue(v)
            return d
        else:
            return value

    def _iterItems(self, items=None):

        if items is None:
            items = {}
        for value in self._itervalues():
            if isitemref(value):
                item = value(True)
                if isitem(item):
                    uuid = item.itsUUID
                    if uuid not in items:
                        items[uuid] = item
                        yield item
            elif isinstance(value, PersistentCollection):
                for v in value._iterItems(items):
                    yield v

    def _iterKeys(self, keys=None):

        if keys is None:
            keys = set()
        for value in self._itervalues():
            if isitemref(value):
                key = value.itsUUID
                if key not in keys:
                    keys.add(key)
                    yield key
            elif isinstance(value, PersistentCollection):
                for v in value._iterKeys(keys):
                    yield v

    def filterItem(self, item, level=0, key=0, _remove=True):
        """
        Remove occurrences of an item in a persistent collection.

        Depending on the C{level} parameter, the item or a collection
        containing the item is destructively removed from this persistent
        collection.

        If C{level} is greater than zero then the collection is recursively
        iterated as a collection of collections and is assumed to have at
        least as many nesting levels as C{level}. When C{level} reaches
        zero, C{item} is sought according to C{key} to the collection's
        type. C{key} is a list or tuple position or a dictionary key and it
        doesn't apply with sets. If C{item} is found, the collection
        containing it is removed from its container collection if C{level}
        was greater than one when C{filterItem} was invoked. Only C{item}
        itself is removed once, according to C{key} otherwise.

        For example:

            - [(i1, 0, 1, 2), (i2, 0, 5)].filterItem(i1, 1) -> [(i2, 0, 5)]

            - { 'a': [(5, i1, 0), (6, i2, 'a')], 'b': [(12, i2, 'b')]}.filterItem(i2, 2, 1) -> { 'a': [(5, i1, 0)], 'b': [] }

        @param item: the item to filter.
        @type item: an Item instance
        @param level: the nesting level of the item to filter.
        @type level: an integer
        @param key: the list position or dictionary key of the item to filter.
        @type key: an integer or a dictionary key
        """
        
        raise NotImplementedError, "%s.filterItem" %(type(self))


class PersistentList(list, PersistentCollection):
    'A persistence aware list, tracking changes into a dirty bit.'

    __slots__ = ['_dirty', '_attribute', '_readOnly', '_item']

    def __init__(self, item=None, attribute=None, values=None, setDirty=True):

        list.__init__(self)
        PersistentCollection.__init__(self, item, attribute)

        if values is not None:
            self.extend(values, setDirty)

    def _copy(self, item, attribute, copyPolicy, copyFn=None):

        copy = type(self)(item, attribute)
        policy = copyPolicy or item.getAttributeAspect(attribute, 'copyPolicy',
                                                       False, None, 'copy')

        for value in self:
            if isitem(value):
                if copyFn is not None:
                    value = copyFn(item, value, policy)
                if value is not Nil:
                    copy.append(value, False)
            elif isinstance(value, ItemValue):
                copy.append(value._copy(item, attribute, copyPolicy, copyFn),
                            False)
            else:
                copy.append(value, False)

        return copy

    def _clone(self, item, attribute):

        clone = type(self)(item, attribute)

        for value in self:
            if isinstance(value, ItemValue):
                value = value._clone(item, attribute)
            clone.append(value, False)

        return clone

    def __contains__(self, value):

        return super(PersistentList, self).__contains__(self._useValue(value))

    def index(self, value):

        return super(PersistentList, self).index(self._useValue(value))

    def count(self, value):

        return super(PersistentList, self).count(self._useValue(value))

    def __setitem__(self, index, value):

        value = PersistentCollection.prepareValue(self._owner(),
                                                  self._attribute,
                                                  value)
        super(PersistentList, self).__setitem__(index, value)
        self._setDirty()

    def __delitem__(self, index):

        super(PersistentList, self).__delitem__(index)        
        self._setDirty()

    def __setslice__(self, start, end, value):

        item = self._owner()
        attribute = self._attribute
        value = [PersistentCollection.prepareValue(item, attribute, v)
                 for v in value]
        super(PersistentList, self).__setslice__(start, end, value)
        self._setDirty()

    def __delslice__(self, start, end):

        super(PersistentList, self).__delslice__(start, end)
        self._setDirty()

    def __iadd__(self, value):

        item = self._owner()
        attribute = self._attribute
        value = [PersistentCollection.prepareValue(item, attribute, v)
                 for v in value]
        super(PersistentList, self).__iadd__(value)
        self._setDirty()

    def __imul__(self, value):

        super(PersistentList, self).__imul__(value)
        self._setDirty()

    def append(self, value, setDirty=True, prepare=True):

        if prepare:
            value = PersistentCollection.prepareValue(self._owner(),
                                                      self._attribute,
                                                      value)
        super(PersistentList, self).append(value)

        if setDirty:
            self._setDirty()

    def add(self, value, setDirty=True, prepare=True):

        if prepare:
            value = PersistentCollection.prepareValue(self._owner(),
                                                      self._attribute,
                                                      value)
        super(PersistentList, self).append(value)

        if setDirty:
            self._setDirty()

    def insert(self, index, value):

        value = PersistentCollection.prepareValue(self._owner(),
                                                  self._attribute,
                                                  value)
        super(PersistentList, self).insert(index, value)
        self._setDirty()

    def pop(self, index=-1):

        value = super(PersistentList, self).pop(index)
        value = self._restoreValue(value)
        self._setDirty()

        return value

    def remove(self, value, setDirty=True):

        super(PersistentList, self).remove(self._useValue(value))
        if setDirty:
            self._setDirty()

    def reverse(self, setDirty=True):

        super(PersistentList, self).reverse()
        if setDirty:
            self._setDirty()

    def sort(self, *args):

        super(PersistentList, self).sort(*args)
        self._setDirty()

    def extend(self, value, setDirty=True):

        item = self._owner()
        attribute = self._attribute
        for v in value:
            self.append(PersistentCollection.prepareValue(item, attribute,
                                                          v, False), False)
        if setDirty:
            self._setDirty()

    def __getitem__(self, key):
        value = super(PersistentList, self).__getitem__(key)
        value = self._restoreValue(value)
        
        return value

    def _get(self, key):

        return super(PersistentList, self).__getitem__(key)

    def __getslice__(self, start, end):

        value = super(PersistentList, self).__getslice__(start, end)
        value = [self._restoreValue(v) for v in value]

        return value

    def __iter__(self):

        for value in super(PersistentList, self).__iter__():
            yield self._restoreValue(value)

    def itervalues(self):

        return self.__iter__()

    def _itervalues(self):

        return super(PersistentList, self).__iter__()

    def filterItem(self, item, level=0, key=0, _remove=True):

        sup = super(PersistentList, self)

        if level == 0:
            if sup.__getitem__(key) == item.itsRef:
                if _remove:
                    self.__delitem__(key)
                return True

        else:
            count = len(self)
            values = [value for value in sup.__iter__()
                      if not value.filterItem(item, level - 1, key, False)]
            if len(values) < count:
                sup.__setslice__(0, count, values)
                self._setDirty()

        return False


class PersistentDict(dict, PersistentCollection):
    'A persistence aware dict, tracking changes into a dirty bit.'

    def __init__(self, item=None, attribute=None, values=None, setDirty=True):

        dict.__init__(self)
        PersistentCollection.__init__(self, item, attribute)

        if values is not None:
            self.update(values, setDirty)

    def _copy(self, item, attribute, copyPolicy, copyFn=None):

        copy = type(self)(item, attribute)
        policy = copyPolicy or item.getAttributeAspect(attribute, 'copyPolicy',
                                                       False, None, 'copy')
        
        for key, value in self.iteritems():
            if isitem(value):
                if copyFn is not None:
                    value = copyFn(item, value, policy)
                if value is not Nil:
                    copy.__setitem__(key, value, False)
            elif isinstance(value, ItemValue):
                copy.__setitem__(key, value._copy(item, attribute, policy,
                                                  copyFn), False)
            else:
                copy.__setitem__(key, value, False)

        return copy

    def _clone(self, item, attribute):

        clone = type(self)(item, attribute)

        for key, value in self.iteritems():
            if isinstance(value, ItemValue):
                value = value._clone(item, attribute)
            clone.__setitem__(key, value, False)

        return clone

    def __delitem__(self, key):

        super(PersistentDict, self).__delitem__(key)
        self._setDirty()

    def __setitem__(self, key, value, setDirty=True, prepare=True):

        if prepare:
            value = PersistentCollection.prepareValue(self._owner(),
                                                      self._attribute,
                                                      value)
        super(PersistentDict, self).__setitem__(key, value)

        if setDirty:
            self._setDirty()

    def clear(self):

        super(PersistentDict, self).clear()
        self._setDirty()

    def update(self, value, setDirty=True):

        item = self._owner()
        attribute = self._attribute
        for k, v in value.iteritems():
            v = PersistentCollection.prepareValue(item, attribute, v, False)
            self.__setitem__(k, v, False)
        if setDirty:
            self._setDirty()

    def setdefault(self, key, value=None):

        if not key in self:
            self._setDirty()

        value = PersistentCollection.prepareValue(self._owner(),
                                                  self._attribute,
                                                  value)

        return super(PersistentDict, self).setdefault(key, value)

    def popitem(self):

        value = super(PersistentDict, self).popitem()
        value = (value[0], self._restoreValue(value[1]))
        self._setDirty()

        return value

    def __getitem__(self, key):

        value = super(PersistentDict, self).__getitem__(key)
        value = self._restoreValue(value)
        
        return value

    def get(self, key, default=None):

        value = super(PersistentDict, self).get(key, default)
        value = self._restoreValue(value)
        
        return value

    def _get(self, key):

        return super(PersistentDict, self).__getitem__(key)

    def itervalues(self):

        for value in super(PersistentDict, self).itervalues():
            yield self._restoreValue(value)

    def iteritems(self):

        for key, value in super(PersistentDict, self).iteritems():
            yield (key, self._restoreValue(value))

    def _itervalues(self):

        return super(PersistentDict, self).itervalues()

    def _iteritems(self):

        return super(PersistentDict, self).iteritems()

    def values(self):

        return list(self.itervalues())

    def _values(self):

        return super(PersistentDict, self).values()

    def items(self):

        return list(self.iteritems())

    def _items(self):

        return super(PersistentDict, self).items()

    def filterItem(self, item, level=0, key=0, _remove=True):

        sup = super(PersistentDict, self)

        if level == 0:
            if sup.__getitem__(key) == item.itsRef:
                if _remove:
                    self.__delitem__(key)
                return True

        else:
            dirty = False
            for k, value in sup.items():
                if value.filterItem(item, level - 1, key, False):
                    sup.__delitem__(k)
                    dirty = True
            if dirty:
                self._setDirty()

        return False


class PersistentTuple(tuple, PersistentCollection):

    def __new__(cls, item=None, attribute=None, values=None, setDirty=True):

        if values is not None:
            values = [cls.prepareValue(item, attribute, value, setDirty)
                      for value in values]

            return super(PersistentTuple, cls).__new__(cls, values)

        return super(PersistentTuple, cls).__new__(cls)

    def __init__(self, item=None, attribute=None, values=None, setDirty=True):

        super(PersistentTuple, self).__init__(item, attribute)

    def _copy(self, item, attribute, copyPolicy, copyFn=None):

        copy = []
        policy = copyPolicy or item.getAttributeAspect(attribute, 'copyPolicy',
                                                       False, None, 'copy')

        for value in self:
            if isitem(value):
                if copyFn is not None:
                    value = copyFn(item, value, policy)
                if value is not Nil:
                    copy.append(value)
            elif isinstance(value, ItemValue):
                copy.append(value._copy(item, attribute, policy, copyFn))
            else:
                copy.append(value)

        return type(self)(item, attribute, copy, False)

    def _clone(self, item, attribute):

        clone = []

        for value in self:
            if isinstance(value, ItemValue):
                value = value._clone(item, attribute)
            clone.append(value)

        return type(self)(item, attribute, clone, False)

    def __getitem__(self, key):

        value = super(PersistentTuple, self).__getitem__(key)
        value = self._restoreValue(value)
        
        return value

    def _get(self, key):

        return super(PersistentTuple, self).__getitem__(key)

    def __contains__(self, value):

        return super(PersistentTuple, self).__contains__(self._useValue(value))

    def __iter__(self):

        for value in super(PersistentTuple, self).__iter__():
            yield self._restoreValue(value)

    def itervalues(self):

        return self.__iter__()

    def _itervalues(self):

        return super(PersistentTuple, self).__iter__()

    def filterItem(self, item, level=0, key=0, _remove=True):

        sup = super(PersistentTuple, self)

        if level == 0:
            if sup.__getitem__(key) == item.itsRef:
                if _remove:
                    raise TypeError, 'tuple is immutable'
                return True

        else:
            count = len(self)
            values = [value for value in sup.__iter__()
                      if not value.filterItem(item, level - 1, key, False)]
            if len(values) < count:
                raise TypeError, 'tuple is immutable'

        return False


class PersistentSet(set, PersistentCollection):
    'A persistence aware set, tracking changes into a dirty bit.'

    def __init__(self, item=None, attribute=None, values=None, setDirty=True):

        set.__init__(self)
        PersistentCollection.__init__(self, item, attribute)

        if values is not None:
            self.update(values, setDirty)

    def _copy(self, item, attribute, copyPolicy, copyFn=None):

        copy = type(self)(item, attribute)
        policy = copyPolicy or item.getAttributeAspect(attribute, 'copyPolicy',
                                                       False, None, 'copy')
        
        for value in self:
            if isitem(value):
                if copyFn is not None:
                    value = copyFn(item, value, policy)
                if value is not Nil:
                    copy.add(value, False)
            elif isinstance(value, ItemValue):
                copy.add(value._copy(item, attribute, policy, copyFn), False)
            else:
                copy.add(value, False)

        return copy

    def _clone(self, item, attribute):

        clone = type(self)(item, attribute)

        for value in self:
            if isinstance(value, ItemValue):
                value = value._clone(item, attribute)
            clone.add(value, False)

        return clone

    def __contains__(self, value):

        return super(PersistentSet, self).__contains__(self._useValue(value))

    def __iter__(self):

        for value in super(PersistentSet, self).__iter__():
            yield self._restoreValue(value)

    def itervalues(self):

        return self.__iter__()

    def _itervalues(self):

        return super(PersistentSet, self).__iter__()

    def add(self, value, setDirty=True, prepare=True):
        
        if prepare:
            value = PersistentCollection.prepareValue(self._owner(),
                                                      self._attribute,
                                                      value)
        super(PersistentSet, self).add(value)

        if setDirty:
            self._setDirty()

    def pop(self):

        value = super(PersistentSet, self).pop()
        value = self._restoreValue(value)
        self._setDirty()

        return value

    def remove(self, value, setDirty=True):

        super(PersistentSet, self).remove(self._useValue(value))
        if setDirty:
            self._setDirty()

    def discard(self, value, setDirty=True):

        super(PersistentSet, self).discard(self._useValue(value))
        if setDirty:
            self._setDirty()

    def clear(self, setDirty=True):

        super(PersistentSet, self).clear()
        if setDirty:
            self._setDirty()

    def update(self, value, setDirty=True):

        item = self._owner()
        attribute = self._attribute
        for v in value:
            if v not in self:
                v = PersistentCollection.prepareValue(item, attribute, v, False)
                self.add(v, False)
        if setDirty:
            self._setDirty()

    def intersection_update(self, value, setDirty=True):

        for v in [v for v in self if v not in value]:
            self.remove(v, False)

        if setDirty:
            self._setDirty()

    def difference_update(self, value, setDirty=True):

        for v in [v for v in self if v in value]:
            self.remove(v, False)

        if setDirty:
            self._setDirty()

    def symmetric_difference_update(self, value, setDirty=True):

        for v in [v for v in self if v in value]:
            self.remove(v, False)

        for v in [v for v in value if v not in self]:
            self.add(v, False)

        if setDirty:
            self._setDirty()

    def filterItem(self, item, level=0, key=0, _remove=True):

        sup = super(PersistentSet, self)

        if level == 0:
            if sup.__contains__(item.itsRef):
                if _remove:
                    self.remove(item)
                return True

        else:
            count = len(self)
            values = [value for value in sup.__iter__()
                      if not value.filterItem(item, level - 1, key, False)]
            if len(values) < count:
                sup.clear()
                sup.update(values)
                self._setDirty()

        return False
