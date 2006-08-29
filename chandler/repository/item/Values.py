#   Copyright (c) 2004-2006 Open Source Applications Foundation
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


from chandlerdb.util.c import \
    UUID, SingleRef, _hash, _combine, isuuid, issingleref, Nil, Default
from chandlerdb.item.c import CValues, CItem, isitem
from chandlerdb.item.ItemError import *
from chandlerdb.item.ItemValue import ItemValue

from repository.util.Path import Path
from repository.util.Lob import Lob
from repository.item.RefCollections import RefList, RefDict
from repository.item.Indexed import Indexed
from repository.schema.TypeHandler import TypeHandler
from repository.persistence.RepositoryError import MergeError


class Values(CValues):

    def __init__(self, item):

        if item is not None:
            self._setItem(item)

    def clear(self):

        for name, value in self._dict.iteritems():
            if isinstance(value, ItemValue):
                value._setOwner(None, None)
            self._setDirty(name)

        self._dict.clear()

    def _getItem(self):

        return self._item

    def _setItem(self, item):

        self._item = item

        for name, value in self._dict.iteritems():
            if isinstance(value, ItemValue):
                value._setOwner(item, name)

    def _refCount(self):

        count = 1

        for value in self._dict.itervalues():
            if isinstance(value, ItemValue):
                count += value._refCount()

        return count

    def _copy(self, orig, copyPolicy, copyFn):

        item = self._item
        for name, value in orig._dict.iteritems():
            if isinstance(value, ItemValue):
                value = value._copy(item, name, copyPolicy, copyFn)
                value._setOwner(item, name)
                self[name] = value

            elif issingleref(value):
                policy = (copyPolicy or
                          item.getAttributeAspect(name, 'copyPolicy',
                                                  False, None, 'copy'))
                other = item.find(value.itsUUID)
                if other is None:
                    self[name] = value
                else:
                    copyOther = copyFn(item, other, policy)
                    if copyOther is not Nil:
                        self[name] = SingleRef(copyOther.itsUUID)

            else:
                self[name] = value

            self._copyFlags(orig, name)

    def _clone(self, orig, exclude):

        item = self._item
        for name, value in orig._dict.iteritems():
            if name not in exclude:
                if isinstance(value, ItemValue):
                    value = value._clone(item, name)
                    value._setOwner(item, name)

                self[name] = value
                self._copyFlags(orig, name)

    def _copyFlags(self, orig, name):

        flags = orig._flags.get(name, 0) & Values.COPYMASK
        if flags != 0:
            self._flags[name] = flags

    def _unload(self, clean=True):

        self._dict.clear()
        self._flags.clear()

    def _setFlags(self, key, flags):

        self._flags[key] = flags

    def _getDirties(self):

        _flags = self._flags
        if _flags:
            return [ key for key, flags in _flags.iteritems()
                     if flags & Values.DIRTY ]

        return []

    def _clearDirties(self):

        _flags = self._flags
        if _flags:
            for key, flags in _flags.iteritems():
                if flags & Values.DIRTY:
                    _flags[key] &= ~Values.DIRTY

        self._clearValueDirties()

    def _clearValueDirties(self):

        # clearing according to flags is not enough, flags not set on new items
        for value in self._dict.itervalues():
            if value is not None and isinstance(value, Indexed):
                value._clearIndexDirties()

    def _writeValues(self, itemWriter, version, withSchema, all):

        item = self._item
        kind = item._kind

        size = 0
        for name, value in self._dict.iteritems():

            flags = self._flags.get(name, 0)
            if flags & Values.TRANSIENT != 0:
                continue
            
            if kind is not None:
                attribute = kind.getAttribute(name, False, item)
                persisted = attribute.c.persisted
            else:
                attribute = None
                persisted = True

            if not persisted:
                continue
            
            if not (all or flags & Values.DIRTY != 0):
                size += itemWriter._unchangedValue(item, name)
                continue
            
            if value is Nil:
                raise ValueError, 'Cannot persist Nil'

            size += itemWriter._value(item, name, value,
                                      version, flags & Values.SAVEMASK, 
                                      withSchema, attribute)

        return size

    def _xmlValues(self, generator, withSchema, version):

        from repository.item.ItemHandler import ValueHandler
        
        item = self._item
        kind = item._kind
        view = item.itsView

        for key, value in self._dict.iteritems():
            if kind is not None:
                attribute = kind.getAttribute(key, False, item)
                c = attribute.c
            else:
                attribute = None

            if attribute is not None:
                persisted = c.persisted
            else:
                persisted = True

            if persisted:
                flags = self._flags.get(key, 0)
                persisted = flags & Values.TRANSIENT == 0
                flags &= Values.SAVEMASK

            if persisted:
                if attribute is not None:
                    attrType = attribute.getAspect('type')
                    attrCard = c.cardinality
                    attrId = attribute.itsUUID
                else:
                    attrType = None
                    attrCard = 'single'
                    attrId = None

                attrs = {}
                if flags:
                    attrs['flags'] = str(flags)

                try:
                    ValueHandler.xmlValue(view, key, value, 'attribute',
                                          attrType, attrCard, attrId, attrs,
                                          generator, withSchema)
                except Exception, e:
                    e.args = ("while saving attribute '%s' of item %s, %s" %(key, item.itsPath, e.args[0]),)
                    raise
        return 0

    def _hashValues(self):

        item = self._item
        kind = item._kind
        view = item.itsView
        hash = 0

        names = self.keys()
        names.sort()
        
        for name in names:
            if kind is not None:
                attribute = kind.getAttribute(name, False, item)
                c = attribute.c
            else:
                attribute = None

            if attribute is not None:
                persisted = c.persisted
            else:
                persisted = True

            if persisted:
                persisted = not self._isTransient(name)

            if persisted:
                hash = _combine(hash, _hash(name))
                value = self[name]
                
                if attribute is not None:
                    attrType = attribute.getAspect('type')
                else:
                    attrType = None

                if attrType is not None:
                    hash = _combine(hash, attrType.hashValue(value))
                else:
                    hash = _combine(hash, TypeHandler.hashValue(view, value))

        return hash

    def _checkValue(self, logger, name, value, attrType, repair):

        if isinstance(value, ItemValue):
            if not value._check(logger, self._item, name, repair):
                return False

        if not attrType.recognizes(value):
            logger.error("Value %s of type %s in attribute '%s' on %s is not recognized by type %s", repr(value), type(value), name, self._item._repr_(), attrType.itsPath)
            return False

        return True

    def _checkCardinality(self, logger, name, value, cardType, attrCard,
                          repair):

        if not (value is None or
                (cardType is None and isitem(value)) or
                (cardType is not None and isinstance(value, cardType))):
            logger.error("Value %s of type %s in attribute '%s' on %s is not an instance of type %s which is required for cardinality '%s'", repr(value), type(value), name, self._item._repr_(), cardType, attrCard)
            return False

        return True

    def check(self, repair=False):
        
        logger = self._item.itsView.logger
        result = True

        for key, value in self._dict.iteritems():
            r = self._verifyAssignment(key, value, logger, repair)
            result = result and r

        return result

    def _verifyAssignment(self, key, value, logger, repair=False):

        item = self._item

        kind = item.itsKind
        if kind is None:
            return True

        attribute = kind.getAttribute(key, True, item)
        if attribute is None:
            if item.isSchema():
                return True
            logger.error('Item %s has a value for attribute %s but its kind %s has no definition for this attribute', item._repr_(), key, kind.itsPath)
            return False

        attrType = attribute.getAspect('type', None)
        if attrType is not None:
            attrCard = attribute.c.cardinality

            if attrCard == 'single':
                return self._checkValue(logger, key, value, attrType, repair)

            elif attrCard == 'list':
                if self._checkCardinality(logger, key, value, list, 'list', repair):
                    result = True
                    for v in value:
                        check = self._checkValue(logger, key, v, attrType, repair)
                        result = result and check
                    return result
                return False

            elif attrCard == 'dict':
                if self._checkCardinality(logger, key, value, dict, 'dict', repair):
                    result = True
                    for v in value.itervalues():
                        check = self._checkValue(logger, key, v, attrType, repair)
                        result = result and check
                    return result
                return False

            elif attrCard == 'set':
                if self._checkCardinality(logger, key, value, set, 'set', repair):
                    result = True
                    for v in value.itervalues():
                        check = self._checkValue(logger, key, v, attrType, repair)
                        result = result and check
                    return result
                return False

        return True

    def _import(self, view):

        item = self._item
        if type(view) is not type(item.itsView):
            for key, value in self._dict.iteritems():
                if isinstance(value, Lob):
                    item.setAttributeValue(key, value.copy(view), self)

    def _collectChanges(self, view, flag, dirties,
                        newChanges, changes, indexChanges,
                        version, newVersion):

        for name in self._getDirties():
            value = self.get(name, Nil)
            newChanges[name] = (False, value)

            if isinstance(value, Indexed):
                value._collectIndexChanges(name, indexChanges)

    def _applyChanges(self, view, flag, dirties, ask, newChanges):

        for name, (isRef, newValue) in newChanges[flag].iteritems():
            if not isRef:
                value = self.get(name, Nil)
                if newValue != value:
                    if name in dirties:
                        newValue = ask(MergeError.VALUE, name, newValue)
                    if newValue is Nil:
                        self._item.removeAttributeValue(name, self, None, True)
                    else:
                        self._item.setAttributeValue(name, newValue, self,
                                                     None, True, True)


class References(Values):

    def _setValue(self, name, other, otherName, noMonitors=False,
                  cardinality=None, alias=None, dictKey=None, otherKey=None,
                  otherCard=None, otherAlias=None):

        item = self._item
        view = item.itsView

        if name in self:
            value = self._getRef(name, None, otherName)
            if value is not None and isitem(value):
                value._references._removeRef(otherName, item)

        if other is not None:
            otherView = other.itsView
            if not (otherView is view or
                    item._isImporting() or
                    other._isImporting()):
                if otherView._isNullView() or view._isNullView():
                    view.importItem(other)
                else:
                    raise ViewMismatchError, (item, other)
                    
            if otherName in other._references:
                value = other._references._getRef(otherName, None, name)
                if value is not None and isitem(value):
                    value._references._removeRef(name, other)

        value = self._setRef(name, other, otherName, cardinality,
                             alias, dictKey, otherKey)

        if other is not None:
            try:
                otherValue = other._references._setRef(otherName, item, name,
                                                       otherCard, otherAlias,
                                                       otherKey, dictKey)
            except:
                self._removeRef(name, other)   # remove dangling ref
                raise
        else:
            otherValue = None

        if not noMonitors:
            if not item._isNoDirty():
                item._fireChanges('set', name)
            if not (other is None or other._isNoDirty()):
                other._fireChanges('set', otherName)

        if value is not None and value._isRefs():
            view._notifyChange(item._collectionChanged,
                               'add', 'collection', name, other.itsUUID)
        if otherValue is not None and otherValue._isRefs():
            view._notifyChange(other._collectionChanged,
                               'add', 'collection', otherName, item.itsUUID)

    def _addRef(self, name, other, otherName=None, fireChanges=False):

        value = self.get(name, None)
        if value is None or not value._isRefs() or other.itsUUID not in value:
            self._setRef(name, other, otherName, None, None, None, None,
                         fireChanges)
            return True

        return False
            
    def _setRef(self, name, other, otherName=None, cardinality=None, alias=None,
                dictKey=None, otherKey=None, fireChanges=False):

        item = self._item
        value = self.get(name)

        if value is None:
            if cardinality is None:
                cardinality = item.getAttributeAspect(name, 'cardinality',
                                                      True, None, 'single')
            if cardinality == 'list':
                self[name] = value = item._refList(name, otherName)
            elif cardinality == 'dict':
                self[name] = value = RefDict(item, name, otherName)
            elif cardinality == 'set':
                raise NoValueForAttributeError, (item, name)
            elif cardinality != 'single':
                raise ValueError, cardinality

        if value is not None and value._isRefs():
            value._setRef(other, alias, dictKey, otherKey, fireChanges)
            if fireChanges:
                item.itsView._notifyChange(item._collectionChanged,
                                           'add', 'collection', name,
                                           other.itsUUID)
                
        else:
            self[name] = value = other
            if not item.itsView.isLoading():
                item.setDirty(item.VDIRTY, name, self, not fireChanges)

        return value

    def _getRef(self, name, other=None, otherName=None, default=Default):

        value = self.get(name, self)
        item = self._item

        if other is None:
            if value is self:
                if default is not Default:
                    return default
                raise KeyError, name
            if value is None or isitem(value) or value._isRefs():
                return value
            if isuuid(value):
                try:
                    other = item.itsView[value]
                except KeyError:
                    raise DanglingRefError, (item, name, value)
                
                self[name] = other
                kind = item.itsKind
                if kind is not None:  # kind may be None during bootstrap
                    if otherName is None:
                        otherName = kind.getOtherName(name, item)
                    other._references._getRef(otherName, item, name)
                return other

            raise TypeError, '%s, type: %s' %(value, type(value))

        if value is other:
            if isuuid(value):
                try:
                    other = item.itsView[value]
                except KeyError:
                    raise DanglingRefError, (item, name, value)
                self[name] = other
            return other

        if value is self or value is None:
            raise BadRefError, (item, name, value, other)

        if value == other.itsUUID:
            self[name] = other
            return other

        if value._isRefs():
            if other in value:
                return other
            else:
                raise DanglingRefError(item, name, other)

        raise BadRefError, (item, name, value, other)
    
    def _removeValue(self, name, other, otherName, dictKey=None):

        otherKey = self._removeRef(name, other, dictKey)
        if not (other is None or other._isRefs()):
            item = self._item
            other._references._removeRef(otherName, item, otherKey)
            #initialValue = other.getAttributeAspect(otherName, 'initialValue',
            #                                        False, None, item)
            #if initialValue is not item:
            #    other._references._setValue(otherName, initialValue, name)

    def _removeRef(self, name, other, dictKey=None, noError=False):

        value = self.get(name, self)
        if value is self:
            if noError:
                return
            raise AssertionError, '_removeRef: no value for %s' %(name)

        item = self._item
        if value is other:
            if other is not None and other._isRefs():
                other.clear()
                dirty = CItem.RDIRTY
            else:
                dirty = CItem.VDIRTY
            del self[name]
            item.setDirty(dirty, name, self, True)
            item._fireChanges('remove', name)
        elif (isuuid(value) and (value == other or
                                 isitem(other) and value == other.itsUUID) or
              isitem(value) and isuuid(other) and value.itsUUID == other):
            del self[name]
            item.setDirty(CItem.VDIRTY, name, self, True)
            item._fireChanges('remove', name)
        elif value._isRefs():
            return value._removeRef(other, dictKey, noError)
        else:
            raise BadRefError, (self._item, name, other, value)
        
    def _unloadValue(self, name, other, otherName, dictKey=None, otherKey=None):

        if other is not None:
            self._unloadRef(name, other, dictKey)
            if isitem(other):
                other._references._unloadRef(otherName, self._item, otherKey)

    def _unloadRef(self, name, other, dictKey=None):

        if not (other is None or isuuid(other)):
            value = self.get(name, None)
            if value is None or value is other:
                self[name] = other.itsUUID
            elif value._isRefs():
                value._unloadRef(other, dictKey)
            elif isuuid(value) and value == other.itsUUID:
                pass
            else:
                raise BadRefError, (self._item, name, other, value)

    def clear(self):

        item = self._item
        refs = item._references
        for name in self.keys():
            # if it wasn't removed by a reflexive bi-ref
            if name in self:
                item.removeAttributeValue(name, refs)

    def _setItem(self, item):

        self._item = item

        for name, value in self._dict.iteritems():
            if value is not None and value._isRefs():
                value._setOwner(item, name)

    def refCount(self, name, loaded):

        count = 0

        value = self._dict.get(name)
        if value is not None:
            if isitem(value):
                count += 1
            elif value._isRefs():
                count += value.refCount(loaded)
            elif not loaded and isuuid(value):
                count += 1

        return count

    def _refCount(self):

        count = 1

        for value in self._dict.itervalues():
            if value is not None:
                if isitem(value):
                    count += 1
                elif value._isRefs():
                    count += value._refCount()

        return count

    # copy a ref from self into copyItem._references
    def _copyRef(self, copyItem, name, other, policy, copyFn):

        value = self._getRef(name, other)
        copyOther = copyFn(copyItem, value, policy)

        if copyOther is not Nil and name not in copyItem._references:
            otherName = copyItem.itsKind.getOtherName(name, copyItem)
            copyItem._references._setValue(name, copyOther, otherName)

    # copy orig._references into self
    def _copy(self, orig, copyPolicy, copyFn):

        item = self._item
        for name, value in orig._dict.iteritems():
            policy = copyPolicy or item.getAttributeAspect(name, 'copyPolicy')
            if value is not None and value._isRefs():
                value._copy(item, name, policy, copyFn)
            else:
                orig._copyRef(item, name, value, policy, copyFn)
            self._copyFlags(orig, name)

    def _clone(self, orig, exclude):

        item = self._item
        kind = item.itsKind

        for name, value in orig._dict.iteritems():
            if name in exclude:
                continue

            self._copyFlags(orig, name)

            if value is None:
                self[name] = None
                continue

            if value._isRefs():
                value._clone(item)  # attribute value is set in _clone()
                continue

            if isuuid(value):
                value = item.itsView[value]

            otherName = kind.getOtherName(name, item)
            otherCard = value.getAttributeAspect(otherName, 'cardinality',
                                                 False, None, 'single')
            if otherCard == 'list':
                self._setValue(name, value, otherName)

    def _unload(self, clean=True):

        if clean:
            for name, value in self._dict.iteritems():
                if value is not None:
                    if value._isRefs():
                        value._unloadRefs()
                    elif isitem(value):
                        item = self._item
                        otherName = item.itsKind.getOtherName(name, item)
                        self._unloadValue(name, value, otherName)

        super(References, self)._unload(clean)

    def _isRefs(self, name):

        try:
            value = self[name]
            return value is not None and value._isRefs()
        except KeyError:
            return False

    def _xmlRef(self, name, other, generator, withSchema, version, attrs,
                previous=None, next=None, alias=None):

        def addAttr(attrs, attr, value):

            if value is not None:
                if isinstance(value, UUID):
                    attrs[attr + 'Type'] = 'uuid'
                    attrs[attr] = value.str64()
                elif isinstance(attr, str) or isinstance(attr, unicode):
                    attrs[attr] = value.encode('utf-8')
                elif isinstance(attr, Path):
                    attrs[attr + 'Type'] = 'path'
                    attrs[attr] = str(value).encode('utf-8')
                else:
                    raise TypeError, "%s, type: %s" %(value, type(value))

        attrs['type'] = 'uuid'

        addAttr(attrs, 'name', name)
        addAttr(attrs, 'previous', previous)
        addAttr(attrs, 'next', next)
        addAttr(attrs, 'alias', alias)

        if withSchema:
            item = self._item
            otherName = item.itsKind.getOtherName(name, item)
            otherCard = other.getAttributeAspect(otherName, 'cardinality',
                                                 False, None, 'single')
            attrs['otherName'] = otherName
            if otherCard != 'single':
                attrs['otherCard'] = otherCard
            uuid = other._uuid
        elif isuuid(other):
            uuid = other
        else:
            uuid = other._uuid

        generator.startElement('ref', attrs)
        generator.characters(uuid.str64())
        generator.endElement('ref')

    def _writeValues(self, itemWriter, version, withSchema, all):

        item = self._item
        kind = item._kind

        size = 0
        for name, value in self._dict.iteritems():

            flags = self._flags.get(name, 0)
            if flags & Values.TRANSIENT != 0:
                continue
            
            if kind is not None:
                attribute = kind.getAttribute(name, False, item)
                persisted = attribute.c.persisted
            else:
                attribute = None
                persisted = True

            if not persisted:
                continue
            
            if not (all or flags & Values.DIRTY != 0):
                size += itemWriter._unchangedValue(item, name)
                continue
            
            if value is Nil:
                raise ValueError, 'Cannot persist Nil'

            if withSchema and value is not None and isuuid(value):
                value = self._getRef(name, value, attribute.c.otherName)

            size += itemWriter._ref(item, name, value,
                                    version, flags & Values.SAVEMASK, 
                                    withSchema, attribute)

        return size

    def _xmlValues(self, generator, withSchema, version):

        item = self._item
        kind = item._kind

        for name, value in self._dict.iteritems():
            attribute = kind.getAttribute(name, False, item)
            if attribute.c.persisted:
                flags = self._flags.get(name, 0) & Values.SAVEMASK
                attrs = { 'id': attribute.itsUUID.str64() }
                if flags:
                    attrs['flags'] = str(flags)

                if value is None:
                    attrs['name'] = name
                    attrs['type'] = 'none'
                    generator.startElement('ref', attrs)
                    generator.endElement('ref')
                else:
                    if withSchema and isuuid(value):
                        value = self._getRef(name, value)
                    
                    if value._isRefs():
                        value._xmlValue(name, item, generator, withSchema,
                                        version, attrs)
                    else:
                        self._xmlRef(name, value, generator, withSchema,
                                     version, attrs)

        return 0

    def _hashValues(self):

        item = self._item
        kind = item._kind
        view = item.itsView
        hash = 0

        names = self.keys()
        names.sort()

        for name in names:
            attribute = kind.getAttribute(name, False, item)
            if attribute.c.persisted:
                hash = _combine(hash, _hash(name))
                value = self[name]
                
                if value is None:
                    hash = _combine(hash, 0)
                elif isuuid(value):
                    hash = _combine(hash, value._hash)
                elif isitem(value):
                    hash = _combine(hash, value._uuid._hash)
                elif value._isRefs():
                    hash = _combine(hash, value._hashValues())
                else:
                    raise TypeError, value

        return hash

    def _clearValueDirties(self):

        # clearing according to flags is not enough, flags not set on new items
        for value in self._dict.itervalues():
            if value is not None and value._isRefs():
                value._clearDirties()

    def _checkRef(self, logger, name, other, repair):

        if other is not None:
            if not isitem(other):
                other = self._item.find(other)
                if other is None:
                    logger.error('DanglingRefError: %s.%s',
                                 self._item.itsPath, name)
                    return False

            if other.isStale():
                logger.error('Found stale item %s at %s.%s',
                             other, self._item.itsPath, name)
                return False

            if other.itsView is not self._item.itsView:
                logger.error("views don't match: %s at %s.%s",
                             other, self._item.itsPath, name)
                return False

        item = self._item
        otherName = item.itsKind.getOtherName(name, item, None)
        if otherName is None:
            logger.error('otherName is None for attribute %s.%s',
                         self._item._kind.itsPath, name)
            return False

        if other is not None:
            if other.itsKind is None:
                raise AssertionError, 'no kind for %s' %(other.itsPath)
            otherOtherName = other.itsKind.getOtherName(otherName, other, None)
            if otherOtherName != name:
                logger.error("otherName for attribute %s.%s, %s, does not match otherName for attribute %s.%s, %s",
                             self._item.itsKind.itsPath, name, otherName,
                             other.itsKind.itsPath, otherName, otherOtherName)
                return False

            otherOther = other._references._getRef(otherName)

            if otherOther is self._item:
                return True
            elif (otherOther._isRefs() and not otherOther._isDict() and
                  self._item in otherOther):
                return True
            elif otherOther._isRefs() and otherOther._isDict():
                return True  # check not yet implemented
            else:
                if otherOther._isRefs():
                    logger.error("%s doesn't contain a reference to %s, yet %s.%s references %s",
                                 otherOther, self._item._repr_(),
                                 self._item._repr_(), name, other._repr_())
                elif isitem(otherOther):
                    logger.error("%s.%s doesn't reference %s.%s but %s",
                                 other._repr_(), otherName, self._item._repr_(),
                                 name, otherOther._repr_())
                else:
                    logger.error("%s.%s doesn't reference %s.%s but %s",
                                 other._repr_(), otherName, self._item._repr_(),
                                 name, otherOther)
                return False

        return True

    def check(self, repair=False):

        item = self._item
        logger = item.itsView.logger
        result = True

        for key, value in self._dict.iteritems():
            if value is not None and isuuid(value):
                value = self._getRef(key, value)
                
            attrCard = item.getAttributeAspect(key, 'cardinality',
                                               False, None, 'single')
            if attrCard == 'single':
                check = self._checkCardinality(logger, key, value,
                                               None, 'single', repair)
                if check:
                    check = self._checkRef(logger, key, value, repair)
            elif attrCard == 'list':
                check = self._checkCardinality(logger, key, value,
                                               RefList, 'list', repair)
                if check:
                    check = value._check(logger, item, key, repair)
            elif attrCard == 'dict':
                check = self._checkCardinality(logger, key, value,
                                               RefDict, 'dict', repair)
                if check:
                    check = value._check(logger, item, key, repair)
            elif attrCard == 'set':
                from repository.item.Sets import AbstractSet
                check = self._checkCardinality(logger, key, value,
                                               AbstractSet, 'set', repair)
                if check:
                    check = value._check(logger, item, key, repair)
            else:
                logger.error("Attribute %s on %s is using a cardinality, '%s', which is not supported, use 'list' instead", key, self._item.itsPath, attrCard)
                check = False

            result = result and check

        return result

    def _verifyAssignment(self, key, other, logger, repair=False):

        item = self._item
        kind = item.itsKind

        if kind is not None and kind.getAttribute(key, True, item) is None:
            logger.error("setting bi-ref on attribute '%s' of %s, but '%s' is not defined for Kind %s %s", key, item._repr_(), key, kind.itsPath, type(item))
            return False

        return True

    def _import(self, view, items, replace):

        item = self._item
        itemView = item.itsView
        sameType = type(view) is type(itemView)

        for key, value in self._dict.items():
            if value is not None:
                if value._isRefs():
                    if sameType or value._isTransient():
                        previous = None
                        for other in value:
                            if other not in items:
                                alias = value.getAlias(other)
                                value.remove(other)
                                localOther = other.findMatch(view, replace)
                                if localOther is not None:
                                    value.insertItem(localOther, previous)
                                    if alias is not None:
                                        value.setAlias(other, alias)
                    else:
                        localValue = view._createRefList(item, value._name, value._otherName, None, True, False, True, UUID())
                        value._copyIndexes(localValue)
                        for other in value:
                            if other in items:
                                localValue._setRef(other, value.getAlias(other))
                            else:
                                localOther = other.findMatch(view, replace)
                                if localOther is not None:
                                    localValue.append(localOther,
                                                      value.getAlias(other))
                                value.remove(other)
                        item._references[key] = localValue
                else:
                    if isuuid(value):
                        value = itemView.find(value)
                    if value not in items:
                        localOther = value.findMatch(view, replace)
                        item.removeAttributeValue(key)
                        if localOther is not None:
                            item.setAttributeValue(key, localOther)

    def _collectChanges(self, view, flag, dirties,
                        newChanges, changes, indexChanges, version, newVersion):

        if flag == CItem.RDIRTY:
            for name in self._getDirties():
                value = self.get(name, Nil)

                if name in dirties:
                    if value is Nil:
                        # if both side removed the value, let it pass
                        # this is enforced in _applyChanges
                        newChanges[name] = ('nil', Nil)
                    elif value is not None and value._isRefs():
                        if value._isSet():
                            newChanges[name] = ('set', value)
                            changes[name] = {}
                            value._collectIndexChanges(name, indexChanges)
                        elif value._isDict():
                            newChanges[name] = \
                                ('dict', 
                                 dict((key, dict(refList._iterChanges()))
                                      for key, refList in value.iteritems()))
                            changes[name] = \
                                dict((key, dict(refList._iterHistory(version, newVersion))) for key, refList in value.iteritems())
                        else:
                            newChanges[name] = ('list',
                                                dict(value._iterChanges()))
                            changes[name] = dict(value._iterHistory(version,
                                                                    newVersion))
                            value._collectIndexChanges(name, indexChanges)
                else:
                    if value is Nil:
                        newChanges[name] = ('nil', Nil)
                    elif value is not None and value._isRefs():
                        if value._isSet():
                            newChanges[name] = ('set', value)
                            value._collectIndexChanges(name, indexChanges)
                        elif value._isDict():
                            newChanges[name] = \
                                ('dict', 
                                 dict((key, dict(refList._iterChanges()))
                                      for key, refList in value.iteritems()))
                        else:
                            newChanges[name] = ('list',
                                                dict(value._iterChanges()))
                            value._collectIndexChanges(name, indexChanges)

        elif flag == CItem.VDIRTY:
            for name in self._getDirties():
                value = self.get(name, Nil)
                if isitem(value):
                    value = value.itsUUID
                elif not (isuuid(value) or value in (None, Nil)):
                    continue
                newChanges[name] = (True, value)

    def _applyChanges(self, view, flag, dirties, ask, newChanges, changes,
                      dangling):

        if flag == CItem.RDIRTY:
            for name, (card, valueChanges) in newChanges[flag].iteritems():
                value = self.get(name, Nil)
                if card == 'set':
                    if not (changes is None or value == valueChanges):
                        if name in dirties:
                            view._e_3_overlap(MergeError.REF, self._item, name)
                    self[name] = valueChanges
                    self._setDirty(name)
                elif name in dirties:
                    if value is Nil and valueChanges:
                        view._e_3_overlap(MergeError.REF, self._item, name)
                    elif valueChanges:
                        if changes is None:
                            if card == 'dict':
                                for key, vc in valueChanges.iteritems():
                                    refList = value._refList(key)
                                    refList._applyChanges(vc, ())
                            else:
                                value._applyChanges(valueChanges, ())
                        else:
                            if card == 'dict':
                                for key, vc in valueChanges.iteritems():
                                    c = changes[flag][name].get(key, ())
                                    refList = value._refList(key)
                                    refList._applyChanges(vc, c)
                            else:
                                value._applyChanges(valueChanges,
                                                    changes[flag][name])
                        self._setDirty(name)
                elif valueChanges is Nil:
                    if value is not Nil:
                        self._removeRef(name, value)
                elif card == 'dict':
                    if value is Nil:
                        item = self._item
                        kind = item.itsKind
                        otherName = kind.getOtherName(name, item)
                        self[name] = value = RefDict(item, name, otherName)
                    for key, vc in valueChanges.iteritems():
                        refList = value._refList(key)
                        refList._applyChanges(vc, ())
                    self._setDirty(name)
                else:
                    if value is Nil:
                        self[name] = value = self._item._refList(name)
                    value._applyChanges(valueChanges, ())
                    self._setDirty(name)

        elif flag == CItem.VDIRTY:
            for name, (isRef, newValue) in newChanges[flag].iteritems():
                if isRef:
                    value = self.get(name, Nil)
                    if isitem(value):
                        value = value.itsUUID
                    elif value is Nil and newValue is Nil:
                        continue
                    elif not (isuuid(value) or value in (None, Nil)):
                        raise AssertionError, ("merging %s.%s" %(self._item._repr_(), name), value)
                    if newValue != value:
                        if name in dirties:
                            if value is Nil:
                                raise AssertionError, ("merging %s.%s" %(self._item._repr_(), name), value)
                            item = view[newValue]
                            if ask(MergeError.REF, name, item) is item:
                                self._setRef(name, newValue)
                                self._setDirty(name)
                                if value is not None:
                                    _item = self._item
                                    kind = _item.itsKind
                                    otherName = kind.getOtherName(name, _item)
                                    dangling.append((value, otherName,
                                                     _item.itsUUID))
                            else:
                                view._e_2_overlap(MergeError.REF, item, name)

                        if newValue is Nil:
                            self._removeRef(name, value)
                        else:
                            self._setRef(name, newValue)
                            self._setDirty(name)
