
__revision__  = "$Revision$"
__date__      = "$Date$"
__copyright__ = "Copyright (c) 2003-2004 Open Source Applications Foundation"
__license__   = "http://osafoundation.org/Chandler_0.1_license_terms.htm"


from chandlerdb.util.c import CLinkedMap, CLink


class LinkedMap(CLinkedMap):

    def _clear_(self):

        super(LinkedMap, self).clear()

    def clear(self):

        self._clear_()
        self._firstKey = None
        self._lastKey = None

    def isEmpty(self):
        
        return len(self) == 0

    def _copy_(self, orig):

        self._clear_()
        
        for key, origLink in orig._dict.iteritems():
            link = CLink(self, origLink.value)
            link._copy_(origLink)
            self._dict[key] = link

        self._firstKey = orig._firstKey
        self._lastKey = orig._lastKey
        
        self._aliases.update(orig._aliases)

    def _remove(self, key):

        del self._dict[key]

    def place(self, key, afterKey=None):
        "Move a key in this collection after another one."

        if key == afterKey:
            return

        current = self._get(key)
        if current._previousKey == afterKey:
            return
        if current._previousKey is not None:
            previous = self._get(current._previousKey)
        else:
            previous = None
        if current._nextKey is not None:
            next = self._get(current._nextKey)
        else:
            next = None

        if afterKey is None:
            after = None
            afterNextKey = self._firstKey
        else:
            after = self._get(afterKey)
            afterNextKey = after._nextKey

        if previous is not None:
            previous._nextKey = (current._nextKey, current._previousKey)
        if next is not None:
            next._previousKey = (current._previousKey, current._nextKey)

        current._nextKey = (afterNextKey, key)
        if afterNextKey is not None:
            self._get(afterNextKey)._previousKey = (key, afterNextKey)
        if after is not None:
            after._nextKey = (key, afterKey)

        current._previousKey = (afterKey, key)
            
    def __delitem__(self, key):

        link = self._get(key)

        if link._previousKey is not None:
            self._get(link._previousKey)._nextKey = (link._nextKey,
                                                     link._previousKey)
        else:
            self._firstKey = link._nextKey
            self.linkChanged(self._head, None)
            
        if link._nextKey is not None:
            self._get(link._nextKey)._previousKey = (link._previousKey,
                                                     link._nextKey)
        else:
            self._lastKey = link._previousKey
            self.linkChanged(self._head, None)

        del self._dict[key]
        self._count -= 1

        if link.alias is not None:
            del self._aliases[link.alias]

        return link

    def has_key(self, key, load=True):

        if self._dict.has_key(key):
            return True

        return load and self._load(key)

    def _contains_(self, key):

        return key in self._dict
            
    def __contains__(self, key):

        if key in self._dict:
            return True

        return self._load(key)

    def get(self, key, default=None, load=True):

        link = self._dict.get(key, default)

        if link is default and load and self._load(key):
            link = self._dict.get(key, default)
        
        if link is not default:
            return link.value

        return default

    def getByAlias(self, alias, default=None, load=True):
        """
        Get the value referenced through its alias.
        
        @param alias: the alias of the item referenced.
        @type key: a string
        @param default: the default value to return if there is no value
        for C{key} in this collection, C{None} by default.
        @type default: anything
        @param load: if the value exists but hasn't been loaded yet,
        this method will return C{default} if this parameter is C{False}.
        @type load: boolean
        @return: a value of the collection or C{default}
        """
        
        key = self._aliases.get(alias)
        if key is None and load:
            key = self.resolveAlias(alias, load)

        if key is None:
            return default
            
        return self.get(key, default, load)

    def resolveAlias(self, alias, load=True):
        """
        Resolve the alias to its corresponding reference key.

        @param alias: the alias to resolve.
        @type alias: a string
        @param load: if the value exists but hasn't been loaded yet,
        this method will return C{None} if this parameter is C{False}.
        @type load: boolean
        @return: a key into the collection or C{None} if the alias does not
        exist.
        """

        return self._aliases.get(alias)

    def setAlias(self, key, alias):
        """
        Set the alias for a key in this mapping.

        The alias must not be set for another key already.
        """

        if alias is not None:
            aliasedKey = self.resolveAlias(alias)
            if not (aliasedKey is None or aliasedKey == key):
                raise ValueError, "alias '%s' already set for key %s" %(alias, aliasedKey)

        link = self._get(key)
        oldAlias = link.alias

        if oldAlias != alias:
            aliases = self._aliases
            self.linkChanged(link, key)

            if aliases:
                if oldAlias is not None and oldAlias in aliases:
                    del aliases[oldAlias]

            link.alias = alias

            if alias is not None:
                aliases[alias] = key
            
        return oldAlias

    def __iter__(self):

        for key in self.iterkeys():
            yield self[key]

    # The _ versions of the iterators below iterate over the currently loaded
    # elements of the linked map and the ones yielding values yield the links
    # themselves.

    def iterkeys(self, firstKey=None, lastKey=None):

        nextKey = firstKey or self._firstKey
        while nextKey != lastKey:
            key = nextKey
            nextKey = self._get(nextKey)._nextKey

            yield key

        if lastKey is not None:
            yield lastKey

    def iteraliases(self, firstKey=None, lastKey=None):

        nextKey = firstKey or self._firstKey
        while nextKey is not None:
            key = nextKey
            link = self._get(nextKey)
            nextKey = link._nextKey
            alias = link.alias

            if alias is not None:
                yield alias, key

            if key == lastKey:
                break

    def _iterkeys(self):

        return self._dict.iterkeys()

    def keys(self):

        return [key for key in self.iterkeys()]

    def _keys(self):

        return self._dict.keys()

    def values(self):

        return [self[key] for key in self.iterkeys()]

    def _values(self):

        return [self._get(key) for key in self._iterkeys()]

    def itervalues(self):

        for key in self.iterkeys():
            yield self[key]

    def _itervalues(self):

        for key in self._iterkeys():
            yield self._get(key)

    def iteritems(self):

        for key in self.iterkeys():
            yield (key, self[key])

    def _iteritems(self):

        for key in self._iterkeys():
            yield (key, self._get(key))

    def items(self):

        return [(key, self[key]) for key in self.iterkeys()]

    def _items(self):

        return [(key, self._get(key)) for key in self._iterkeys()]
