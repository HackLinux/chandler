
__revision__  = "$Revision$"
__date__      = "$Date$"
__copyright__ = "Copyright (c) 2003-2004 Open Source Applications Foundation"
__license__   = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

from struct import pack, unpack

from chandlerdb.util.c import UUID, _hash, isuuid
from chandlerdb.item.c import Nil, Default, isitem, CValues
from chandlerdb.item.ItemValue import ItemValue
from repository.item.Item import Item
from repository.item.Sets import AbstractSet
from repository.item.Values import Values, References
from repository.item.ItemIO import \
    ItemWriter, ItemReader, ItemPurger, ValueReader
from repository.item.PersistentCollections \
     import PersistentCollection, PersistentList, PersistentDict, PersistentSet
from repository.schema.TypeHandler import TypeHandler
from repository.persistence.RepositoryError \
     import LoadError, LoadValueError, MergeError, SaveValueError
from repository.persistence.DBContainer import HashTuple


class DBItemWriter(ItemWriter):

    def __init__(self, store):

        super(DBItemWriter, self).__init__()

        self.store = store
        self.valueBuffer = []
        self.dataBuffer = []

    def writeItem(self, item, version):

        self.values = []
        
        self.uParent = DBItemWriter.NOITEM

        if not ((item._status & (Item.NEW | Item.MERGED)) != 0 or
                item._version == 0):
            self.oldValues = self.store._items.getItemValues(item._version,
                                                             item._uuid)
            if self.oldValues is None:
                raise AssertionError, ("Record not found for %s, version %s" %(item._repr_(), item._version))
        else:
            self.oldValues = None

        if item._isKDirty() and not item.isNew():
            prevKind = item._pastKind or DBItemWriter.NOITEM
        else:
            prevKind = None

        size = super(DBItemWriter, self).writeItem(item, version)
        size += self.store._items.saveItem(self.valueBuffer,
                                           item._uuid, version,
                                           self.uKind, prevKind,
                                           item._status & Item.SAVEMASK,
                                           self.uParent, self.name,
                                           self.moduleName, self.className,
                                           self.values,
                                           item._values._getDirties(),
                                           item._references._getDirties())

        return size

    def writeString(self, buffer, value):

        if isinstance(value, unicode):
            value = value.encode('utf-8')
            size = len(value)
            buffer.append(pack('>i', size + 1))
        else:
            size = len(value)
            buffer.append(pack('>i', -(size + 1)))
            
        buffer.append(value)

        return 4 + size

    def writeSymbol(self, buffer, value):

        if isinstance(value, unicode):
            value = value.encode('ascii')

        buffer.append(pack('>H', len(value)))
        buffer.append(value)

        return 2 + len(value)

    def writeBoolean(self, buffer, value):

        if value is None:
            buffer.append('\2')
        elif value:
            buffer.append('\1')
        else:
            buffer.append('\0')

        return 1

    def writeInteger(self, buffer, value):

        buffer.append(pack('>i', value))
        return 4

    def writeLong(self, buffer, value):
        
        buffer.append(pack('>q', value))
        return 8
        
    def writeFloat(self, buffer, value):

        buffer.append(pack('>d', value))
        return 8

    def writeUUID(self, buffer, value):

        buffer.append(value._uuid)
        return 16

    def writeLob(self, buffer, value, indexed):

        self.lobs.append((value, indexed))
        size = self.writeUUID(buffer, value)
        size += self.writeBoolean(buffer, indexed)

        return size

    def writeIndex(self, buffer, value):

        self.indexes.append(value)
        return self.writeUUID(buffer, value)

    def writeValue(self, buffer, item, version, value, withSchema, attrType):

        flags = DBItemWriter.SINGLE | DBItemWriter.VALUE
        attrType = self._type(buffer, flags, item, value, True,
                              withSchema, attrType)
        return attrType.writeValue(self, buffer, item, version,
                                   value, withSchema)

    def writeList(self, buffer, item, version, value, withSchema, attrType):

        flags = DBItemWriter.LIST | DBItemWriter.VALUE
        attrType = self._type(buffer, flags, item, value, False,
                              withSchema, attrType)
        buffer.append(pack('>I', len(value)))
        size = 4
        for v in value:
            size += self.writeValue(buffer, item, version,
                                    v, withSchema, attrType)

        return size

    def writeSet(self, buffer, item, version, value, withSchema, attrType):

        flags = DBItemWriter.SET | DBItemWriter.VALUE
        attrType = self._type(buffer, flags, item, value, False,
                              withSchema, attrType)
        buffer.append(pack('>I', len(value)))
        size = 4
        for v in value:
            size += self.writeValue(buffer, item, version,
                                    v, withSchema, attrType)

        return size

    def writeDict(self, buffer, item, version, value, withSchema, attrType):

        flags = DBItemWriter.DICT | DBItemWriter.VALUE
        attrType = self._type(buffer, flags, item, value, False,
                              withSchema, attrType)
        buffer.append(pack('>I', len(value)))
        size = 4
        for k, v in value._iteritems():
            size += self.writeValue(buffer, item, version,
                                    k, False, None)
            size += self.writeValue(buffer, item, version,
                                    v, withSchema, attrType)

        return size

    def writeIndexes(self, buffer, item, version, value):

        if value._indexes:
            buffer.append(pack('>H', len(value._indexes)))
            size = 2 + value._saveIndexes(self, buffer, version)
        else:
            buffer.append('\0\0')
            size = 2

        return size

    def _kind(self, kind):

        if kind is None:
            self.uKind = DBItemWriter.NOITEM
        else:
            self.uKind = kind.itsUUID

        return 0

    def _parent(self, parent, isContainer):

        if parent is None:
            self.uParent = DBItemWriter.NOITEM
        else:
            self.uParent = parent.itsUUID

        return 0

    def _name(self, name):

        self.name = name
        return 0

    def _className(self, moduleName, className):

        self.moduleName = moduleName
        self.className = className

        return 0

    def _children(self, item, version, all):

        if item._children is not None:
            return item._children._saveValues(version)

        return 0

    def _acls(self, item, version, all):

        size = 0
        if item._status & Item.ADIRTY:
            store = self.store
            uuid = item._uuid
            for name, acl in item._acls.iteritems():
                size += store.saveACL(version, uuid, name, acl)

        return size

    def _values(self, item, version, withSchema, all):

        return item._values._writeValues(self, version, withSchema, all)

    def _references(self, item, version, withSchema, all):

        return item._references._writeValues(self, version, withSchema, all)

    def _value(self, item, name, value, version, flags, withSchema, attribute):

        self.lobs = []
        self.indexes = []

        uValue = UUID()
        self.values.append((name, uValue))

        if attribute is None:
            uAttr = DBItemWriter.NOITEM
            attrCard = 'single'
            attrType = None
            indexed = False
        else:
            uAttr = attribute._uuid
            c = attribute.c
            attrCard = c.cardinality
            attrType = attribute.getAspect('type', None)
            indexed = c.indexed
            
        buffer = self.dataBuffer
        del buffer[:]

        if indexed:
            flags |= CValues.INDEXED
        buffer.append(chr(flags))

        if withSchema:
            self.writeSymbol(buffer, name)

        try:
            if attrCard == 'single':
                self.writeValue(buffer, item, version,
                                value, withSchema, attrType)
            elif attrCard == 'list':
                self.writeList(buffer, item, version,
                               value, withSchema, attrType)
            elif attrCard == 'set':
                self.writeSet(buffer, item, version,
                              value, withSchema, attrType)
            elif attrCard == 'dict':
                self.writeDict(buffer, item, version,
                               value, withSchema, attrType)
        except Exception, e:
            raise #SaveValueError, (item, name, e)

        if indexed:

            if attrType is None:
                valueType = TypeHandler.typeHandler(item.itsView, value)
            elif attrType.isAlias():
                valueType = attrType.type(value)
            else:
                valueType = attrType

            valueType.indexValue(self, item, attribute, version, value)

        for uuid, indexed in self.lobs:
            self.writeUUID(buffer, uuid)
            self.writeBoolean(buffer, indexed)

        for uuid in self.indexes:
            self.writeUUID(buffer, uuid)

        buffer.append(pack('>H', len(self.lobs)))
        buffer.append(pack('>H', len(self.indexes)))

        return self.store._values.c.saveValue(self.store.txn,
                                              uAttr, uValue, ''.join(buffer))

    def indexValue(self, value, item, attribute, version):

        self.store._index.indexValue(item.itsView._getIndexWriter(),
                                     value, item.itsUUID, attribute.itsUUID,
                                     version)

    def indexReader(self, reader, item, attribute, version):

        self.store._index.indexReader(item.itsView._getIndexWriter(),
                                      reader, item.itsUUID, attribute.itsUUID,
                                      version)

    def _unchangedValue(self, item, name):

        try:
            self.values.append((name, self.oldValues[_hash(name)]))
        except KeyError:
            raise AssertionError, "unchanged value for '%s' not found" %(name)

        return 0

    def _type(self, buffer, flags, item, value, verify, withSchema, attrType):

        if attrType is None:
            if verify:
                attrType = TypeHandler.typeHandler(item.itsView, value)
                typeId = attrType._uuid
            else:
                typeId = None

        elif attrType.isAlias():
            if verify:
                aliasType = attrType.type(value)
                if aliasType is None:
                    raise TypeError, "%s does not alias type of value '%s' of type %s" %(attrType.itsPath, value, type(value))
                attrType = aliasType
                typeId = attrType._uuid
            else:
                typeId = None
            
        else:
            if verify and not attrType.recognizes(value):
                raise TypeError, "value '%s' of type %s is not recognized by type %s" %(value, type(value), attrType.itsPath)

            if withSchema:
                typeId = attrType._uuid
            else:
                typeId = None

        if typeId is None:
            buffer.append(chr(flags))
        else:
            flags |= DBItemWriter.TYPED
            buffer.append(chr(flags))
            buffer.append(typeId._uuid)

        return attrType

    def _ref(self, item, name, value, version, flags, withSchema, attribute):

        uValue = UUID()
        self.values.append((name, uValue))
        size = 0

        buffer = self.dataBuffer
        del buffer[:]

        buffer.append(chr(flags))
        if withSchema:
            self.writeSymbol(buffer, name)

        if value is None:
            buffer.append(chr(DBItemWriter.NONE | DBItemWriter.REF))

        elif isuuid(value):
            if withSchema:
                raise AssertionError, 'withSchema is True'
            buffer.append(chr(DBItemWriter.SINGLE | DBItemWriter.REF))
            buffer.append(value._uuid)

        elif isitem(value):
            buffer.append(chr(DBItemWriter.SINGLE | DBItemWriter.REF))
            buffer.append(value.itsUUID._uuid)

        elif value._isRefs():
            attrCard = attribute.c.cardinality
            if attrCard == 'list':
                flags = DBItemWriter.LIST | DBItemWriter.REF
                if withSchema:
                    flags |= DBItemWriter.TYPED
                buffer.append(chr(flags))
                buffer.append(value.uuid._uuid)
                if withSchema:
                    self.writeSymbol(buffer, item.itsKind.getOtherName(name, item))
                size += value._saveValues(version)

            elif attrCard == 'set':
                flags = DBItemWriter.SET | DBItemWriter.REF
                buffer.append(chr(flags))
                self.writeString(buffer, value.makeString(value))

            else:
                raise NotImplementedError, attrCard

            self.indexes = []
            size += self.writeIndexes(buffer, item, version, value)
            for uuid in self.indexes:
                self.writeUUID(buffer, uuid)
            buffer.append(pack('>H', len(self.indexes)))

        else:
            raise TypeError, value

        size += self.store._values.c.saveValue(self.store.txn,
                                               attribute.itsUUID, uValue,
                                               ''.join(buffer))

        return size

    TYPED    = 0x01
    VALUE    = 0x02
    REF      = 0x04
    SET      = 0x08
    SINGLE   = 0x10
    LIST     = 0x20
    DICT     = 0x40
    NONE     = 0x80
    
    NOITEM = UUID('6d4df428-32a7-11d9-f701-000393db837c')


class DBValueReader(ValueReader):

    def __init__(self, store, status):

        self.store = store
        self.status = status

        self.uItem = None
        self.name = None

    def readValue(self, view, uValue):

        store = self.store
        uAttr, vFlags, data = store._values.c.loadValue(store.txn, uValue)
        withSchema = (self.status & Item.CORESCHEMA) != 0

        if withSchema:
            attribute = None
            offset, name = self.readSymbol(0, data)
        else:
            attribute = view[uAttr]
            offset, name = 0, attribute.itsName


        flags = ord(data[offset])

        if flags & DBItemWriter.VALUE:
            offset, value = self._value(offset, data, None, withSchema,
                                        attribute, view, name, [])
            return value

        elif flags & DBItemWriter.REF:
            if flags & DBItemWriter.SINGLE:
                offset, uuid = self.readUUID(offset + 1, data)
                return view[uuid]

            elif flags & DBItemWriter.NONE:
                return None

            offset, uuid = self.readUUID(offset + 1, data)
            return uuid

        else:
            raise ValueError, flags

    def _value(self, offset, data, kind, withSchema, attribute, view, name,
               afterLoadHooks):

        if withSchema:
            attrType = None
        else:
            attrType = attribute.getAspect('type', None)

        flags = ord(data[offset])

        if flags & DBItemWriter.SINGLE:
            return self._readValue(offset, data, withSchema, attrType,
                                   view, name, afterLoadHooks)
        elif flags & DBItemWriter.LIST:
            return self._readList(offset, data, withSchema, attrType,
                                  view, name, afterLoadHooks)
        elif flags & DBItemWriter.SET:
            return self._readSet(offset, data, withSchema, attrType,
                                 view, name, afterLoadHooks)
        elif flags & DBItemWriter.DICT:
            return self._readDict(offset, data, withSchema, attrType,
                                  view, name, afterLoadHooks)
        else:
            raise LoadValueError, (self.name or self.uItem, name,
                                   "invalid cardinality: 0x%x" %(flags))

    def _ref(self, offset, data, kind, withSchema, attribute, view, name,
             afterLoadHooks):

        flags = ord(data[offset])
        offset += 1
        
        if flags & DBItemWriter.NONE:
            return offset, None

        elif flags & DBItemWriter.SINGLE:
            return self.readUUID(offset, data)

        elif flags & DBItemWriter.LIST:
            offset, uuid = self.readUUID(offset, data)
            if withSchema:
                offset, otherName = self.readSymbol(offset, data)
            else:
                otherName = kind.getOtherName(name, None)
            value = view._createRefList(None, name, otherName,
                                        True, False, False, uuid)
            offset = self._readIndexes(offset, data, value, afterLoadHooks)

            return offset, value

        elif flags & DBItemWriter.SET:
            offset, string = self.readString(offset, data)
            value = AbstractSet.makeValue(string)
            value._setView(view)
            offset = self._readIndexes(offset, data, value, afterLoadHooks)

            return offset, value

        else:
            raise LoadValueError, (self.name or self.uItem, name,
                                   "invalid cardinality: 0x%x" %(flags))

    def _type(self, offset, data, attrType, view, name):

        if ord(data[offset]) & DBItemWriter.TYPED:
            typeId = UUID(data[offset+1:offset+17])
            try:
                return offset+17, view[typeId]
            except KeyError:
                raise LoadValueError, (self.name or self.uItem, name,
                                       "type not found: %s" %(typeId))

        return offset+1, attrType

    def _readValue(self, offset, data, withSchema, attrType, view, name,
                   afterLoadHooks):

        offset, attrType = self._type(offset, data, attrType, view, name)
        if attrType is None:
            raise LoadValueError, (self.name or self.uItem, name,
                                   "value type is None")
        
        return attrType.readValue(self, offset, data, withSchema, view, name,
                                  afterLoadHooks)

    def _readList(self, offset, data, withSchema, attrType, view, name,
                  afterLoadHooks):

        offset, attrType = self._type(offset, data, attrType, view, name)
        count, = unpack('>I', data[offset:offset+4])
        offset += 4

        value = PersistentList()
        for i in xrange(count):
            offset, v = self._readValue(offset, data, withSchema, attrType,
                                        view, name, afterLoadHooks)
            value.append(v, False, False)

        return offset, value

    def _readSet(self, offset, data, withSchema, attrType, view, name,
                 afterLoadHooks):

        offset, attrType = self._type(offset, data, attrType, view, name)
        count, = unpack('>I', data[offset:offset+4])
        offset += 4

        value = PersistentSet()
        for i in xrange(count):
            offset, v = self._readValue(offset, data, withSchema, attrType,
                                        view, name, afterLoadHooks)
            value.add(v, False, False)

        return offset, value

    def _readDict(self, offset, data, withSchema, attrType, view, name,
                  afterLoadHooks):

        offset, attrType = self._type(offset, data, attrType, view, name)
        count, = unpack('>I', data[offset:offset+4])
        offset += 4

        value = PersistentDict()
        for i in xrange(count):
            offset, k = self._readValue(offset, data, False, None,
                                        view, name, afterLoadHooks)
            offset, v = self._readValue(offset, data, withSchema, attrType,
                                        view, name, afterLoadHooks)
            value.__setitem__(k, v, False, False)

        return offset, value

    def _readIndexes(self, offset, data, value, afterLoadHooks):

        count, = unpack('>H', data[offset:offset+2])
        offset += 2

        if count > 0:
            for i in xrange(count):
                offset = value._loadIndex(self, offset, data)
            afterLoadHooks.append(value._restoreIndexes)

        return offset

    def readString(self, offset, data):

        offset, len = offset+4, unpack('>i', data[offset:offset+4])[0]
        if len >= 0:
            len -= 1
            return offset+len, unicode(data[offset:offset+len], 'utf-8')
        else:
            len += 1
            return offset-len, data[offset:offset-len]

    def readSymbol(self, offset, data):

        offset, len, = offset+2, unpack('>H', data[offset:offset+2])[0]
        return offset+len, data[offset:offset+len]

    def readBoolean(self, offset, data):

        value = data[offset]

        if value == '\0':
            value = False
        elif value == '\1':
            value = True
        else:
            value = None

        return offset+1, value

    def readInteger(self, offset, data):
        return offset+4, unpack('>i', data[offset:offset+4])[0]

    def readLong(self, offset, data):
        return offset+8, unpack('>q', data[offset:offset+8])[0]
        
    def readFloat(self, offset, data):
        return offset+8, unpack('>d', data[offset:offset+8])[0]

    def readUUID(self, offset, data):
        return offset+16, UUID(data[offset:offset+16])

    def readLob(self, offset, data):
        offset, uuid = self.readUUID(offset, data)
        offset, indexed = self.readBoolean(offset, data)
        return offset, uuid, indexed

    def readIndex(self, offset, data):
        return self.readUUID(offset, data)


class DBItemReader(ItemReader, DBValueReader):

    def __init__(self, store, uItem,
                 version, uKind, status, uParent,
                 name, moduleName, className, uValues):

        self.store = store
        self.uItem = uItem
        self.version = version
        self.uKind = uKind
        self.status = status
        self.uParent = uParent
        self.name = name
        self.moduleName = moduleName
        self.className = className
        self.uValues = uValues

    def __repr__(self):

        if self.name is not None:
            name = ' ' + self.name
        else:
            name = ''

        if self.className is not None:
            className = ' (%s)' %(self.className)
        else:
            className = ''
            
        return "<ItemReader%s:%s %s>" %(className, name, self.uItem.str16())

    def readItem(self, view, afterLoadHooks):

        status = self.status
        withSchema = (status & Item.CORESCHEMA) != 0
        isContainer = (status & Item.CONTAINER) != 0

        status &= (Item.CORESCHEMA | Item.P_WATCHED)
        watcherDispatch = view._watcherDispatch
        if watcherDispatch and self.uItem in watcherDispatch:
            status |= Item.T_WATCHED

        kind = self._kind(self.uKind, withSchema, view, afterLoadHooks)
        parent = self._parent(self.uParent, withSchema, view, afterLoadHooks)
        cls = self._class(self.moduleName, self.className, withSchema, kind,
                          view, afterLoadHooks)

        values = Values(None)
        references = References(None)

        self._values(values, references, self.uValues, kind,
                     withSchema, view, afterLoadHooks)

        instance = view._reuseItemInstance(self.uItem)
        if instance is not None:
            if cls is not type(instance):
                instance.__class__ = cls
            item = self.item = instance
            status |= item._status & item.PINNED
        else:
            item = self.item = cls.__new__(cls)

        item._fillItem(self.name, parent, kind, self.uItem,
                       values, references, status, self.version,
                       afterLoadHooks, False)

        if isContainer:
            item._children = view._createChildren(item, False)
            
        if kind is not None:
            afterLoadHooks.append(lambda view: kind._setupClass(cls))

        if hasattr(cls, 'onItemLoad'):
            afterLoadHooks.append(item.onItemLoad)

        return item

    def getUUID(self):
        return self.uItem

    def getVersion(self):
        return self.version

    def isDeleted(self):
        return (self.status & Item.DELETED) != 0

    def _kind(self, uuid, withSchema, view, afterLoadHooks):

        if uuid == DBItemWriter.NOITEM:
            return None
        
        kind = super(DBItemReader, self)._kind(uuid, withSchema,
                                               view, afterLoadHooks)
        if kind is None:
            if withSchema:
                afterLoadHooks.append(self._setKind)
            else:
                raise LoadError, (self.name or self.uItem,
                                  "kind not found: %s" %(uuid))

        return kind

    def _setKind(self, view):

        if self.item._kind is None:
            try:
                kind = view[self.uKind]
            except KeyError:
                raise LoadError, (self.name or self.uItem,
                                  "kind not found: %s" %(uuid))
            else:
                self.item._kind = kind
                kind._setupClass(type(self.item))

    def _parent(self, uuid, withSchema, view, afterLoadHooks):

        if uuid == view.itsUUID:
            return view
        
        parent = super(DBItemReader, self)._parent(uuid, withSchema,
                                                   view, afterLoadHooks)
        if parent is None:
            afterLoadHooks.append(self._move)

        return parent

    def _move(self, view):

        if self.item._parent is None:
            try:
                parent = view[self.uParent]
            except KeyError:
                raise LoadError, (self.name or self.uItem,
                                  "parent not found: %s" %(self.uParent))
            else:
                self.item.move(parent)

    def _values(self, values, references, uValues, kind,
                withSchema, view, afterLoadHooks):

        store = self.store
        c = store._values.c
        txn = store.txn

        for uuid in uValues:
            attrId, vFlags, data = c.loadValue(txn, uuid)
            if withSchema:
                attribute = None
                offset, name = self.readSymbol(0, data)
            else:
                try:
                    attribute = view[attrId]
                except KeyError:
                    raise LoadError, (self.name or self.uItem,
                                      "attribute not found: %s" %(attrId))
                else:
                    offset, name = 0, attribute.itsName

            flags = ord(data[offset])

            if flags & DBItemWriter.VALUE:
                offset, value = self._value(offset, data, kind, withSchema,
                                            attribute, view, name,
                                            afterLoadHooks)
                d = values
            elif flags & DBItemWriter.REF:
                offset, value = self._ref(offset, data, kind, withSchema,
                                          attribute, view, name,
                                          afterLoadHooks)
                d = references
            else:
                raise LoadValueError, (self.name or self.uItem, name,
                                       "not value or ref: 0x%x" %(flags))

            if value is not Nil:
                d[name] = value
                if vFlags != '\0':
                    vFlags = ord(vFlags) & CValues.SAVEMASK
                    if vFlags:
                        d._setFlags(name, vFlags)


class DBItemMergeReader(DBItemReader):

    def __init__(self, store, item, dirties, mergeFn, *args):

        super(DBItemMergeReader, self).__init__(store, item._uuid, *args)

        self.item = item
        self.dirties = dirties
        self.mergeFn = mergeFn

    def readItem(self, view, afterLoadHooks):

        status = self.status
        withSchema = (status & Item.CORESCHEMA) != 0
        kind = self._kind(self.uKind, withSchema, view, afterLoadHooks)

        self._values(self.item._values._prepareMerge(),
                     self.item._references._prepareMerge(),
                     self.uValues, kind, withSchema, view, afterLoadHooks)


class DBItemVMergeReader(DBItemMergeReader):

    def _value(self, offset, data, kind, withSchema, attribute, view, name,
               afterLoadHooks):

        value = Nil
        if name in self.dirties:
            offset, value = super(DBItemVMergeReader, self)._value(offset, data, kind, withSchema, attribute, view, name, afterLoadHooks)
            item = self.item
            reason = MergeError.VALUE
            originalValues = item._values
            if originalValues._isDirty(name):
                originalValue = originalValues.get(name, Nil)
                if value == originalValue:
                    value = Nil

                elif (isinstance(originalValue, AbstractSet) and
                      originalValue._merge(value)):
                    value = originalValue

                elif self.mergeFn is not None:
                    mergedValue = self.mergeFn(reason, item, name, value)
                    if mergedValue is Default:
                        if hasattr(type(item), 'onItemMerge'):
                            mergedValue = item.onItemMerge(reason, name, value)
                            if mergedValue is Default:
                                self._e_4_overlap(reason, item, name)
                            else:
                                value = mergedValue
                        else:
                            self._e_3_overlap(reason, item, name)
                    else:
                        value = mergedValue
                            
                elif hasattr(type(item), 'onItemMerge'):
                    mergedValue = item.onItemMerge(reason, name, value)
                    if mergedValue is Default:
                        self._e_4_overlap(reason, item, name)
                    else:
                        value = mergedValue
                    
                else:
                    self._e_1_overlap(reason, item, name)

        return offset, value
    
    def _ref(self, offset, data, kind, withSchema, attribute, view, name,
             afterLoadHooks):

        if name not in self.dirties:
            return offset, Nil

        flags = ord(data[offset])
        offset += 1

        if flags & DBItemWriter.LIST:
            return offset, Nil

        if flags & DBItemWriter.NONE:
            itemRef = None
        elif flags & DBItemWriter.SINGLE:
            offset, itemRef = self.readUUID(offset, data)
        else:
            raise LoadValueError, (self.name or self.uItem, name,
                                   "invalid cardinality: 0x%x" %(flags))

        origItem = self.item
        origRef = origItem._references.get(name, None)

        if self.item._references._isDirty(name):
            if origRef is not None:
                if isuuid(origRef):
                    if origRef == itemRef:
                        return offset, Nil
                    origRef = origItem._references._getRef(name, origRef)

                elif origRef._uuid == itemRef:
                    return offset, Nil

                self._e_2_overlap(MergeError.REF, self.item, name)

            elif itemRef is None:
                return offset, Nil

        if origRef is not None:
            if not (isitem(origRef) and origRef._uuid == itemRef or
                    isuuid(origRef) and origRef == itemRef):
                if isuuid(origRef):
                    origRef = origItem._references._getRef(name, origRef)
                origItem._references._unloadValue(name, origRef,
                                                  kind.getOtherName(name, None))

        return offset, itemRef

    def _e_1_overlap(self, code, item, name):
        
        raise MergeError, ('values', item, 'merging values failed because no onItemMerge callback method was defined on %s and no mergeFn callback was passed to refresh(), overlapping attribute: %s' %(type(item), name), code)

    def _e_2_overlap(self, code, item, name):

        raise MergeError, ('values', item, 'merging refs is not yet implement\
ed, overlapping attribute: %s' %(name), MergeError.BUG)

    def _e_3_overlap(self, code, item, name):
        
        raise MergeError, ('values', item, 'merging values failed because no onItemMerge callback method was defined on %s and the mergeFn callback passed to refresh punted the merge, overlapping attribute: %s' %(type(item), name), code)

    def _e_4_overlap(self, code, item, name):
        
        raise MergeError, ('values', item, 'merging values failed because the onItemMerge callback defined on %s the merge, overlapping attribute: %s' %(type(item), name), code)


class DBItemRMergeReader(DBItemMergeReader):

    def __init__(self, store, item, dirties, oldVersion, *args):

        super(DBItemRMergeReader, self).__init__(store, item, dirties,
                                                 None, *args)

        self.merged = []
        self.oldVersion = oldVersion
        self.oldDirties = item._references._getDirties()

    def readItem(self, view, afterLoadHooks):

        super(DBItemRMergeReader, self).readItem(view, afterLoadHooks)

        if self.merged:
            self.dirties = HashTuple(filter(lambda h: h not in self.merged,
                                            self.dirties))
        self.item._references._dirties = self.dirties

    def _value(self, offset, data, kind, withSchema, attribute, view, name,
               afterLoadHooks):

        return offset, Nil
    
    def _ref(self, offset, data, kind, withSchema, attribute, view, name,
             afterLoadHooks):

        if name in self.dirties:
            flags = ord(data[offset])

            if flags & DBItemWriter.LIST:
                if name in self.oldDirties:
                    value = self.item._references.get(name, None)
                    if value is not None and value._isRefs():
                        value._mergeChanges(self.oldVersion, self.version)
                        self.merged.append(self.dirties.hash(name))

                        return offset, Nil

                else:
                    offset, value = super(DBItemRMergeReader, self)._ref(offset, data, kind, withSchema, attribute, view, name, afterLoadHooks)
                    value._setOwner(self.item, name)
    
                    return offset, value

            elif flags & DBItemWriter.SET:
                offset, value = super(DBItemRMergeReader, self)._ref(offset, data, kind, withSchema, attribute, view, name, afterLoadHooks)
                value._setOwner(self.item, name)
    
                if name in self.oldDirties:
                    originalValue = self.item._references.get(name, None)
                    if value is not None and value._isRefs():
                        if originalValue._merge(value):
                            value = originalValue
                        else:
                            raise NotImplementedError, 'bi-directional set merge with mergeFn'

                return offset, value

            else:
                raise ValueError, flags

        return offset, Nil


class DBItemPurger(ItemPurger):

    def __init__(self, txn, store, uItem, keepValues,
                 indexSearcher, indexReader, status):

        self.store = store
        self.uItem = uItem

        self.keep = set(keepValues)
        self.done = set()

        withSchema = (status & Item.CORESCHEMA) != 0
        keepOne = (status & Item.DELETED) == 0
        keepDocuments = set()

        for value in keepValues:
            uAttr, vFlags, data = store._values.c.loadValue(txn, value)

            if withSchema:
                offset = self.skipSymbol(0, data)
            else:
                offset = 0
                
            flags = ord(data[offset])
            offset += 1

            if flags & DBItemWriter.VALUE:
                for uuid, indexed in self.iterLobs(flags, data):
                    self.keep.add(uuid)
                    if indexed:                     # full text indexed
                        keepDocuments.add(uAttr)
                if ord(vFlags) & CValues.INDEXED:   # full text indexed
                    keepDocuments.add(uAttr)

            elif flags & DBItemWriter.REF:
                if flags & DBItemWriter.LIST:
                    self.keep.add(UUID(data[offset:offset+16]))

            self.keep.update(self.iterIndexes(flags, data))

        self.itemCount = 0
        self.valueCount = self.lobCount = self.blockCount = self.indexCount = 0
        self.refCount, self.nameCount = \
            store._refs.purgeRefs(txn, uItem, keepOne)
        self.documentCount = \
            store._index.purgeDocuments(indexSearcher, indexReader,
                                        uItem, keepDocuments)

    def iterLobs(self, flags, data):

        if flags & DBItemWriter.VALUE:
            lobCount, indexCount = unpack('>HH', data[-4:])

            lobStart = -(lobCount * 17 + indexCount * 16) - 4
            for i in xrange(lobCount):
                uuid = UUID(data[lobStart:lobStart+16])
                indexed = data[lobStart+16] == '\1'
                lobStart += 17
                yield uuid, indexed

    def iterIndexes(self, flags, data):

        if flags & DBItemWriter.VALUE:
            indexCount, = unpack('>H', data[-2:])
            indexStart = -indexCount * 16 - 4
            for i in xrange(indexCount):
                yield UUID(data[indexStart:indexStart+16])
                indexStart += 16

        elif flags & DBItemWriter.REF:
            if flags & (DBItemWriter.LIST | DBItemWriter.SET):
                indexCount, = unpack('>H', data[-2:])
                indexStart = -indexCount * 16 - 2
                for i in xrange(indexCount):
                    yield UUID(data[indexStart:indexStart+16])
                    indexStart += 16

    def skipSymbol(self, offset, data):
        offset, len, = offset+2, unpack('>H', data[offset:offset+2])[0]
        return offset + len

    def purgeItem(self, txn, values, version, status):

        withSchema = (status & Item.CORESCHEMA) != 0
        store = self.store
        keep = self.keep
        done = self.done

        for uValue in values:
            if not (uValue in keep or uValue in done):
                uAttr, vFlags, data = store._values.c.loadValue(txn, uValue)

                indexedLob = False
                if withSchema:
                    offset = self.skipSymbol(0, data)
                else:
                    offset = 0

                flags = ord(data[offset])
                offset += 1

                if flags & DBItemWriter.VALUE:
                    for uuid, indexed in self.iterLobs(flags, data):
                        if not (uuid in keep or uuid in done):
                            count = store._lobs.purgeLob(txn, uuid)
                            self.lobCount += count[0]
                            self.blockCount += count[1]
                            done.add(uuid)
                    for uuid in self.iterIndexes(flags, data):
                        if uuid not in done:
                            self.indexCount += store._indexes.purgeIndex(txn, uuid, uuid in keep)
                            done.add(uuid)

                elif flags & DBItemWriter.REF and flags & DBItemWriter.LIST:
                    uuid = UUID(data[offset:offset+16])
                    if uuid not in done:
                        count = store._refs.purgeRefs(txn, uuid, uuid in keep)
                        self.refCount += count[0]
                        self.nameCount += count[1]
                        done.add(uuid)
                    for uuid in self.iterIndexes(flags, data):
                        if uuid not in done:
                            self.indexCount += store._indexes.purgeIndex(txn, uuid, uuid in keep)
                            done.add(uuid)

                self.valueCount += store._values.purgeValue(txn, uValue)
                done.add(uValue)

        self.itemCount += store._items.purgeItem(txn, self.uItem, version)
