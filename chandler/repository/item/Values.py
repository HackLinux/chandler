
__revision__  = "$Revision$"
__date__      = "$Date$"
__copyright__ = "Copyright (c) 2004 Open Source Applications Foundation"
__license__   = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

from chandlerdb.util.c import UUID, SingleRef, _hash, _combine, isuuid
from chandlerdb.item.c import Nil, Default, CValues, CItem
from chandlerdb.item.ItemError import *
from chandlerdb.item.ItemValue import ItemValue

from repository.util.Path import Path
from repository.util.Lob import Lob
from repository.item.RefCollections import RefList
from repository.schema.TypeHandler import TypeHandler


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

            elif isinstance(value, SingleRef):
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

    def _prepareMerge(self):

        if not hasattr(self, '_original'):
            self._original = self.copy()

        return self

    def _commitMerge(self):

        try:
            del self._original
        except AttributeError:
            pass

    def _revertMerge(self):

        try:
            self.update(self._original)
            del self._original
        except AttributeError:
            pass
        
    def _checkValue(self, logger, name, value, attrType):

        if isinstance(value, ItemValue):
            if not value._check(logger, self._item, name):
                return False

        if not attrType.recognizes(value):
            logger.error("Value %s of type %s in attribute '%s' on %s is not recognized by type %s", repr(value), type(value), name, self._item._repr_(), attrType.itsPath)
            return False

        return True

    def _checkCardinality(self, logger, name, value, cardType, attrCard):

        if not (value is None or
                (cardType is None and isitem(value)) or
                (cardType is not None and isinstance(value, cardType))):
            logger.error("Value %s of type %s in attribute '%s' on %s is not an instance of type %s which is required for cardinality '%s'", repr(value), type(value), name, self._item._repr_(), cardType, attrCard)
            return False

        return True

    def check(self):
        
        logger = self._item.itsView.logger
        result = True

        for key, value in self._dict.iteritems():
            r = self._verifyAssignment(key, value, logger)
            result = result and r

        return result

    def _verifyAssignment(self, key, value, logger):

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
                return self._checkValue(logger, key, value, attrType)

            elif attrCard == 'list':
                if self._checkCardinality(logger, key, value, list, 'list'):
                    result = True
                    for v in value:
                        check = self._checkValue(logger, key, v, attrType)
                        result = result and check
                    return result
                return False

            elif attrCard == 'dict':
                if self._checkCardinality(logger, key, value, dict, 'dict'):
                    result = True
                    for v in value.itervalues():
                        check = self._checkValue(logger, key, v, attrType)
                        result = result and check
                    return result
                return False

            elif attrCard == 'set':
                if self._checkCardinality(logger, key, value, set, 'set'):
                    result = True
                    for v in value.itervalues():
                        check = self._checkValue(logger, key, v, attrType)
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
    

class References(Values):

    def _setValue(self, name, other, otherName, noMonitors=False,
                  cardinality=None, alias=None,
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

        value = self._setRef(name, other, otherName, cardinality, alias)
        if other is not None:
            otherValue = other._references._setRef(otherName, item, name,
                                                   otherCard, otherAlias)
        else:
            otherValue = None

        if not noMonitors:
            if not item._isNoDirty():
                item._fireChanges('set', name)
            if not (other is None or other._isNoDirty()):
                other._fireChanges('set', otherName)

        if value is not None and value._isRefList():
            view._notifyChange(item._collectionChanged,
                               'add', 'collection', name, other)
        if otherValue is not None and otherValue._isRefList():
            view._notifyChange(other._collectionChanged,
                               'add', 'collection', otherName, item)
            
    def _setRef(self, name, other, otherName, cardinality=None, alias=None):

        item = self._item
        value = self.get(name)

        if item.itsView._isVerify():
            logger = item.itsView.logger
            if not self._verifyAssignment(name, other, logger):
                raise ValueError, "Assigning %s to attribute '%s' on %s didn't match schema" %(other._repr_(), name, item._repr_())

        if value is None:
            if cardinality is None:
                cardinality = item.getAttributeAspect(name, 'cardinality',
                                                      True, None, 'single')
            if cardinality == 'list':
                self[name] = value = item._refList(name, otherName)

        if value is not None and value._isRefList():
            value._setRef(other, alias)
        else:
            self[name] = value = other
            if not item.itsView.isLoading():
                item.setDirty(item.VDIRTY, name, self, True)

        return value

    def _getRef(self, name, other=None, otherName=None, default=Default):

        value = self.get(name, self)
        item = self._item

        if other is None:
            if value is self:
                if default is not Default:
                    return default
                raise KeyError, name
            if value is None or isitem(value) or value._isRefList():
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

        if value._isRefList():
            if other in value:
                return other
            else:
                raise DanglingRefError(item, name, other)

        raise BadRefError, (item, name, value, other)
    
    def _removeValue(self, name, other, otherName):

        self._removeRef(name, other)
        if not (other is None or other._isRefList()):
            item = self._item
            other._references._removeRef(otherName, item)
            #initialValue = other.getAttributeAspect(otherName, 'initialValue',
            #                                        False, None, item)
            #if initialValue is not item:
            #    other._references._setValue(otherName, initialValue, name)

    def _removeRef(self, name, other):

        value = self.get(name, self)
        if value is self:
            raise AssertionError, '_removeRef: no value for %s' %(name)

        item = self._item
        if value is other:
            if other is not None and other._isRefList():
                other.clear()
                dirty = CItem.RDIRTY
            else:
                dirty = CItem.VDIRTY
            del self[name]
            item.setDirty(dirty, name, self, True)
            item._fireChanges('remove', name)
        elif isuuid(value) and isitem(other) and value == other._uuid:
            del self[name]
            item.setDirty(CItem.VDIRTY, name, self, True)
            item._fireChanges('remove', name)
        elif value._isRefList():
            value._removeRef(other)
        else:
            raise BadRefError, (self._item, name, other, value)
        
    def _unloadValue(self, name, other, otherName):

        if other is not None:
            self._unloadRef(name, other, otherName)
            if isitem(other):
                other._references._unloadRef(otherName, self._item, name)

    def _unloadRef(self, name, other, otherName):

        if not (other is None or isuuid(other)):
            value = self.get(name, None)
            if value is None or value is other:
                self[name] = other._uuid
            elif value._isRefList():
                value._unloadRef(other)
            elif isuuid(value) and value == other._uuid:
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

        for value in self._dict.itervalues():
            if value is not None and value._isRefList():
                value._setItem(item, False)

    def refCount(self, loaded):

        count = 0

        for value in self._dict.itervalues():
            if value is not None:
                if isitem(value):
                    count += 1
                elif value._isRefList():
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
                elif value._isRefList():
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
            if value is not None and value._isRefList():
                value._copy(item, name, policy, copyFn)
            else:
                orig._copyRef(item, name, value, policy, copyFn)
            self._copyFlags(orig, name)

    def _unload(self, clean=True):

        if clean:
            for name, value in self._dict.iteritems():
                if value is not None:
                    if value._isRefList():
                        value._unload()
                    elif isitem(value):
                        item = self._item
                        otherName = item.itsKind.getOtherName(name, item)
                        self._unloadValue(name, value, otherName)

        super(References, self)._unload(clean)

    def _isRefList(self, name):

        try:
            value = self[name]
            return value is not None and value._isRefList()
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
                    
                    if value._isRefList():
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
                elif value._isRefList():
                    hash = _combine(hash, value._hashValues())
                else:
                    raise TypeError, value

        return hash

    def _clearDirties(self):

        super(References, self)._clearDirties()
        # clearing according to flags is not enough, flags not set on new items
        for value in self._dict.itervalues():
            if value is not None and value._isRefList():
                value._clearDirties()

    def _commitMerge(self):

        try:
            del self._original
        except AttributeError:
            pass

        try:
            dirties = self._dirties
            del self._dirties
        except AttributeError:
            dirties = None

        for key, value in self._dict.iteritems():
            if value is not None and value._isRefList():
                if dirties is not None and key in dirties:
                    value._clear_()
                else:
                    try:
                        del value._original
                    except AttributeError:
                        pass

    def _revertMerge(self):

        try:
            original = self._original
            self.update(original)
            del self._original
        except AttributeError:
            original = self

        try:
            del self._dirties
        except AttributeError:
            pass

        for key, value in original._dict.iteritems():
            try:
                if value is not None and value._isRefList():
                    self[key] = value._original
                    del value._original
            except AttributeError:
                pass

    def _checkRef(self, logger, name, other):

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
            if other._kind is None:
                raise AssertionError, 'no kind for %s' %(other.itsPath)
            otherOtherName = other.itsKind.getOtherName(otherName, other, None)
            if otherOtherName != name:
                logger.error("otherName for attribute %s.%s, %s, does not match otherName for attribute %s.%s, %s",
                             self._item._kind.itsPath, name, otherName,
                             other._kind.itsPath, otherName, otherOtherName)
                return False

            otherOther = other._references._getRef(otherName)
            if not (otherOther is self._item or
                    otherOther._isRefList() and self._item in otherOther):
                if otherOther._isRefList():
                    logger.error("%s doesn't contain a reference to %s, yet %s.%s references %s",
                                 otherOther, self._item._repr_(),
                                 self._item._repr_(), otherName, other._repr_())
                else:
                    logger.error("%s.%s doesn't reference %s.%s but %s",
                                 other._repr_(), otherName, self._item._repr_(),
                                 name, otherOther)
                return False

        return True

    def check(self):

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
                                               None, 'single')
                if check:
                    check = self._checkRef(logger, key, value)
            elif attrCard == 'list':
                check = self._checkCardinality(logger, key, value,
                                               RefList, 'list')
                if check:
                    check = value.check(logger, key, item)
            elif attrCard == 'dict':
                logger.error("Attribute %s on %s is using deprecated 'dict' cardinality, use 'list' instead", key, self._item.itsPath)
                check = value.check(logger, key, item)
                check = False

            else:
                logger.error("Attribute %s on %s is using a cardinality, '%s', which is not supported, use 'list' instead", key, self._item.itsPath, attrCard)
                check = False

            result = result and check

        return result

    def _verifyAssignment(self, name, other, logger):

        item = self._item
        kind = item.itsKind

        if kind is not None and kind.getAttribute(name, True, item) is None:
            logger.error("setting bi-ref on attribute '%s' of %s, but '%s' is not defined for Kind %s", name, item._repr_(), name, kind.itsPath)
            return False

        return True

    def _import(self, view, items, replace):

        item = self._item
        itemView = item.itsView
        sameType = type(view) is type(itemView)

        for key, value in self._dict.items():
            if value is not None:
                if value._isRefList():
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
                        localValue = view._createRefList(item, value._name, value._otherName, True, False, True, UUID())
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
