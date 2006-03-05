
__revision__  = "$Revision: 9611 $"
__date__      = "$Date: 2006-02-24 13:28:58 -0800 (Fri, 24 Feb 2006) $"
__copyright__ = "Copyright (c) 2003-2004 Open Source Applications Foundation"
__license__   = "http://osafoundation.org/Chandler_0.1_license_terms.htm"


from repository.item.Item import Item


class CollectionClass(type):

    def __init__(cls, name, bases, clsdict):

        if not hasattr(cls, '__collection__'):  # local or inherited
            raise AttributeError, (cls, '__collection__ is undefined')

        if '__collection__' in clsdict:         # local
            cls.__delegates__ = clsdict['__collection__'],


class Collection(Item):
    """
    Collection instances are items wrapping a collection attribute value and
    provide a C{subscribers} ref collection for clients to subscribe to their
    notifications. Subscriber items must provide a C{subscribesTo} inverse
    attribute and a method of the following signature:
        C{onCollectionNotification(op, collection, name, item)}
    where C{op} is one of C{add}, C{remove}, C{refresh} or C{changed},
    C{collection} is the Collection item, C{name} is the attribute
    containing the collection value and C{item} the item in the collection
    that was added, removed, refreshed or changed.

    This class is abstract. Base concrete subclasses must use the
    C{CollectionClass} metaclass, must be declared tied to a kind that
    provides the collection attribute, and must declare its name as in the
    example below:

        __metaclass__ = CollectionClass
        __collection__ = 'attrName'

    The type of collection value chosen (as declared in the kind definition)
    determines which methods are delegated from this item to the collection
    value, typically an C{AbstractSet} subclass instance or a C{RefList}
    instance.
    """

    def _collectionChanged(self, op, change, name, other):

        if change == 'dispatch':

            for subscriber in self.subscribers:
                subscriber.onCollectionNotification(op, self, name, other)

            view = self.itsView
            subscribers = view._subscribers.get(self.itsUUID)
            if subscribers:
                for subscriber in subscribers:
                    view[subscriber].onCollectionNotification(op, self, name, other)

        else:

            view = self.itsView
            if self.subscribers or view._subscribers.get(self.itsUUID):
                view.queueNotification(self, op, change, name, other)

            super(Collection, self)._collectionChanged(op, change, name, other)

    def __contains__(self, obj):

        return obj in getattr(self, self.__collection__)

    def __iter__(self):

        return iter(getattr(self, self.__collection__))

    def __len__(self):

        return len(getattr(self, self.__collection__))

    def __nonzero__(self):

        return True

    def _inspect(self, indent=0):

        return super(Collection, self)._inspectCollection(self.__collection__,
                                                          indent)

    def add(self, other):

        try:
            add = getattr(self, self.__collection__).add
        except AttributeError:
            raise NotImplementedError, (type(self), 'add not implemented')
        else:
            return add(other)

    def remove(self, other):

        try:
            remove = getattr(self, self.__collection__).remove
        except AttributeError:
            raise NotImplementedError, (type(self), 'remove not implemented')
        else:
            return remove(other)

    def notificationQueueSubscribe(self, subscriber):

        self.subscribers.add(subscriber)

    def notificationQueueUnsubscribe(self, subscriber):

        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)
