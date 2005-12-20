""" Classes used for Contacts parcel kinds
"""

__copyright__ = "Copyright (c) 2003-2004 Open Source Applications Foundation"
__license__   = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

__all__ = ['ContactName', 'Contact']

from osaf.pim import items
from application import schema
from i18n import OSAFMessageFactory as _


class ContactName(items.ContentItem):
    "A very simple (and incomplete) representation of a person's name"

    firstName = schema.One(schema.Text, initialValue=u"")
    lastName  = schema.One(schema.Text, initialValue=u"")
    contact = schema.One("Contact", inverse="contactName")

    schema.addClouds(
        sharing = schema.Cloud(firstName, lastName)
    )


class Contact(items.ContentItem):
    """
    An entry in an address book.

    Typically represents either a person or a company.

    Issues: We might want to keep track of lots of sharing information like
    'Permissions I've given them', 'Items of mine they've subscribed to',
    'Items of theirs I've subscribed to', etc.
    """
    schema.kindInfo(displayName=_(u"Contact"), displayAttribute="emailAddress")

    itemsCreated = schema.Sequence(
        displayName=u"Items Created",
        doc = "List of content items created by this user.",
        inverse=items.ContentItem.creator,
    )

    contactName = schema.One(
        ContactName, inverse=ContactName.contact, initialValue=None
    )

    emailAddress = schema.One(schema.Text,
        displayName = _(u"Email Address"),
        initialValue = u""
    )

    itemsLastModified = schema.Sequence(
        items.ContentItem,
        displayName=u"Items Last Modified",
        doc="List of content items last modified by this user.",
        inverse=items.ContentItem.lastModifiedBy
    )

    requestedTasks = schema.Sequence(
        "osaf.pim.tasks.TaskMixin",
        displayName=u"Requested Tasks",
        doc="List of tasks requested by this user.",
        inverse="requestor"
    )

    taskRequests= schema.Sequence(
        "osaf.pim.tasks.TaskMixin",
        displayName=u"Task Requests",
        doc="List of tasks requested for this user.",
        otherName="requestee"   # XXX other end points to ContentItem???
    )

    organizedEvents= schema.Sequence(
        "osaf.pim.calendar.Calendar.CalendarEventMixin",
        displayName=u"Organized Events",
        doc="List of events this user has organized.",
        inverse="organizer"
    )

    participatingEvents= schema.Sequence(
        "osaf.pim.calendar.Calendar.CalendarEventMixin",
        displayName=u"Participating Events",
        doc="List of events this user is a participant.",
        inverse="participants"
    )

    sharerOf= schema.Sequence(  # Share
        displayName=u"Sharer Of",
        doc="List of shares shared by this user.",
        otherName="sharer"
    )

    shareeOf= schema.Sequence(  # Share
        displayName=u"Sharee Of",
        doc="List of shares for which this user is a sharee.",
        otherName="sharees"
    )

    # <!-- redirections -->

    who   = schema.Descriptor(redirectTo="contactName")
    about = schema.Descriptor(redirectTo="displayName")
    date  = schema.Descriptor(redirectTo="createdOn")

    schema.addClouds(
        sharing = schema.Cloud(emailAddress, byCloud=[contactName])
    )

    def InitOutgoingAttributes (self):
        """ Init any attributes on ourself that are appropriate for
        a new outgoing item.
        """
        try:
            super(Contact, self).InitOutgoingAttributes ()
        except AttributeError:
            pass

        self.contactName = ContactName()
        self.contactName.firstName = ''
        self.contactName.lastName = ''


    # Cache "me" for fast lookup; used by getCurrentMeContact()
    meContactID = None


    def getContactForEmailAddress(cls, view, address):
        """ Given an email address string, find (or create) a matching contact.

        @param view: The repository view object
        @type view: L{repository.persistence.RepositoryView}
        @param address: An email address to use for looking up a contact
        @type address: string
        @return: A Contact
        """

        for item in cls.iterItems(view):
            if item.emailAddress == address:
                return item # Just return the first match

        # Need to create a new Contact
        contact = Contact(itsView=view)
        contact.emailAddress = address
        contact.contactName = None
        return contact

    getContactForEmailAddress = classmethod(getContactForEmailAddress)
