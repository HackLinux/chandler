""" Classes used for Mail parcel kinds
"""

__revision__  = "$Revision$"
__date__      = "$Date$"
__copyright__ = "Copyright (c) 2003-2004 Open Source Applications Foundation"
__license__   = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

__all__ = [
    'AccountBase', 'DownloadAccountBase', 'EmailAddress', 'IMAPAccount',
    'IMAPDelivery', 'MIMEBase', 'MIMEBinary', 'MIMEContainer', 'MIMENote',
    'MIMESecurity', 'MIMEText', 'MailDeliveryBase', 'MailDeliveryError',
    'MailMessage', 'MailMessageMixin', 'POPAccount', 'POPDelivery',
    'SMTPAccount', 'SMTPDelivery',
    'getCurrentSMTPAccount', 'getCurrentMailAccount', 'ACCOUNT_TYPES',
]


import application
from application import schema
import repository.item.Item as Item
import items, notes
import application.Globals as Globals
import email.Utils as Utils
import re as re
import chandlerdb.item.ItemError as ItemError

from repository.util.Path import Path
from i18n import OSAFMessageFactory as _
from osaf import messages

"""
Design Issues:
      1. Is tries really needed
      2. Date sent string could probally be gotten rid of
"""

MAIL_DEFAULT_PATH = "//userdata"


def getCurrentSMTPAccount(view, uuid=None, includeInactives=False):
    """
        This function returns a tuple containing:
        1. The an C{SMTPAccount} account
        2. The ReplyTo C{EmailAddress} associated with the C{SMTPAccounts}
           parent which will either be a POP or IMAP Acccount.

    @param uuid: The C{uuid} of the C{SMTPAccount}. If no C{uuid} passed will return
                 the current  C{SMTPAccount}
    @type uuid: C{uuid}
    @return C{tuple} in the form (C{SMTPAccount}, C{EmailAddress})
    """

    smtpAccount = None
    replyToAddress = None

    if uuid is not None:
        smtpAccount = view.findUUID(uuid)

        if smtpAccount is not None:
            for acc in smtpAccount.accounts:
                if acc.isActive or includeInactives:
                    if acc.host and acc.username and \
                       hasattr(acc, 'replyToAddress'):
                        replyToAddress = acc.replyToAddress
                        break

        return (smtpAccount, replyToAddress)

    """Get the default Mail Account"""
    parentAccount = schema.ns('osaf.app', view).currentMailAccount.item

    if parentAccount is not None:
        if hasattr(parentAccount, 'replyToAddress'):
            replyToAddress = parentAccount.replyToAddress

        """Get the default SMTP Account"""
        try:
            smtpAccount = parentAccount.defaultSMTPAccount

        except ItemError.NoValueForAttributeError:
            pass

    return(smtpAccount, replyToAddress)


def getCurrentMailAccount(view, uuid=None):
    """
    This function returns either an C{IMAPAccount} or C{POPAccount} in the
    Repository. If uuid is not None will try and retrieve the account that
    has the uuid passed.  Otherwise the method will try and retrieve the
    current C{IMAPAccount} or C{POPAccount}.

    @param uuid: The C{uuid} of the account. If no C{uuid} passed will return the current account
    @type uuid: C{uuid}
    @return C{IMAPAccount} or C{POPAccount}
    """

    if uuid is not None:
        account = view.findUUID(uuid)

    else:
        account = schema.ns('osaf.app', view).currentMailAccount.item

    return account


class connectionSecurityEnum(schema.Enumeration):
    schema.kindInfo(displayName=u"Connection Security Enumeration")
    values = "NONE", "TLS", "SSL"


class AccountBase(items.ContentItem):

    schema.kindInfo(
        displayName=u"Account base kind",
        description="The base kind for various account kinds, such as "
                    "IMAP, SMTP, WebDav"
    )

    numRetries = schema.One(
        schema.Integer,
        displayName = _(u'Number of Retries'),
        doc = 'How many times to retry before giving up',
        initialValue = 1,
    )
    username = schema.One(
        schema.String,
        displayName = messages.USERNAME,
        doc = 'The account login name',
        initialValue = '',
    )
    password = schema.One(
        schema.String,
        displayName = _(u'Password'),
        doc = 'This could either be a password or some other sort of '
              'authentication info. We can use it for whatever is needed '
              'for this account type.\n\n'
            'Issues:\n'
            '   This should not be a simple string. We need some solution for '
            'encrypting it.\n',
        initialValue = '',
    )
    host = schema.One(
        schema.String,
        displayName = _(u'Host'),
        doc = 'The hostname of the account',
        initialValue = '',
    )
    port = schema.One(
        schema.Integer, displayName = _(u'Port'), doc = 'The port number to use',
    )
    connectionSecurity = schema.One(
        connectionSecurityEnum,
        displayName = _(u'Connection Security'),
        doc = 'The security mechanism to leverage for a network connection',
        initialValue = 'NONE',
    )
    pollingFrequency = schema.One(
        schema.Integer,
        displayName = u'Polling frequency',
        doc = 'Frequency in seconds',
        initialValue = 300,
    )
    mailMessages = schema.Sequence(
        'MailMessageMixin',
        displayName = u'Mail Messages',
        doc = 'Mail Messages sent or retrieved with this account ',
        initialValue = [],
        inverse = 'parentAccount',
    )
    timeout = schema.One(
        schema.Integer,
        displayName = _(u'Timeout'),
        doc = 'The number of seconds before timing out a stalled connection',
        initialValue = 60,
    )
    isActive = schema.One(
        schema.Boolean,
        displayName = u'Is active',
        doc = 'Whether or not an account should be used for sending or '
              'fetching email',
        initialValue = True,
    )

    __default_path__ = MAIL_DEFAULT_PATH

    @classmethod
    def getActiveAccounts(cls, view):
        for item in cls.iterItems(view):
            if item.isActive and item.host and item.username:
                yield item


class DownloadAccountBase(AccountBase):

    schema.kindInfo(
        displayName=u"Download Account Base",
        description="Base Account for protocols that download mail",
    )

    defaultSMTPAccount = schema.One(
        'SMTPAccount',
        displayName = _(u'Default SMTP Account'),
        doc = 'Which SMTP account to use for sending mail from this account',
        initialValue = None,
        inverse = 'accounts',
    )
    downloadMax = schema.One(
        schema.Integer,
        displayName = u'Download Max',
        doc = 'The maximum number of messages to download before forcing a repository commit',
        initialValue = 20,
    )
    replyToAddress = schema.One(
        'EmailAddress',
        displayName = _(u'Reply-To Address'),
        initialValue = None,
        inverse = 'accounts',
    )
    emailAddress = schema.One(
        displayName = u'Reply-To Address (Redirect)',
        redirectTo = 'replyToAddress.emailAddress',
    )
    fullName = schema.One(
        displayName = u'Full Name (Redirect)',
        redirectTo = 'replyToAddress.fullName',
    )


class SMTPAccount(AccountBase):

    accountType = "SMTP"

    schema.kindInfo(
        displayName=_(u"SMTP Account"),
        description="An SMTP Account",
    )

    port = schema.One(
        schema.Integer,
        displayName = _(u'Port'),
        doc = 'The non-SSL port number to use\n\n'
            "Issues:\n"
            "   In order to get a custom initialValue for this attribute for an "
            "SMTPAccount, I defined a 'duplicate' attribute, also named "
            "'port', which normally would have been inherited from AccountBase\n",
        initialValue = 25,
    )
    useAuth = schema.One(
        schema.Boolean,
        displayName = _(u'Use Authentication'),
        doc = 'Whether or not to use authentication when sending mail',
        initialValue = False,
    )
    accounts = schema.Sequence(
        DownloadAccountBase,
        displayName = u'Accounts',
        doc = 'Which accounts use this SMTP account as their default',
        initialValue = [],
        inverse = DownloadAccountBase.defaultSMTPAccount,
    )
    signature = schema.One(
        schema.String,
        description =
            "Issues:\n"
            '   Basic signiture addition to an outgoing message will be refined '
            'in future releases\n',
    )


class IMAPAccount(DownloadAccountBase):

    accountType = "IMAP"

    schema.kindInfo(
        displayName = _(u"IMAP Account"),
        description = "An IMAP Account",
    )

    port = schema.One(
        schema.Integer,
        displayName = _(u'Port'),
        doc = 'The non-SSL port number to use\n\n'
            "Issues:\n"
            "   In order to get a custom initialValue for this attribute for "
            "an IMAPAccount, I defined a 'duplicate' attribute, also named "
            "'port', which normally would have been inherited from AccountBase\n",
        initialValue = 143,
    )
    messageDownloadSequence = schema.One(
        schema.Long,
        displayName = u'Message Download Sequence',
        initialValue = 0L,
    )


class POPAccount(DownloadAccountBase):

    accountType = "POP"

    schema.kindInfo(
        displayName = _(u"POP Account"),
        description = "An POP Account",
    )
    port = schema.One(
        schema.Integer,
        displayName = _(u'Port'),
        doc = 'The non-SSL port number to use\n\n'
            "Issues:\n"
            "   In order to get a custom initialValue for this attribute for "
            "a POPAccount, I defined a 'duplicate' attribute, also named "
            "'port', which normally would have been inherited from AccountBase\n",
        initialValue = 110,
    )
    downloadedMessageUIDS = schema.Mapping(
        schema.String,
        displayName = u'Downloaded Message UID',
        doc = 'Used for quick look up to discover if a message has already been downloaded',
        initialValue = {},
    )
    leaveOnServer = schema.One(
        schema.Boolean,
        displayName = u'Leave Mail On Server',
        doc = 'Whether or not to leave messages on the server after downloading',
        initialValue = True,
    )


class MailDeliveryError(items.ContentItem):

    schema.kindInfo(
        displayName=u"Mail Delivery Error kind",
        description=
            "Contains the error data associated with a MailDelivery Type"
    )

    errorCode = schema.One(
        schema.Integer,
        displayName = u'The Error Code',
        doc = 'The Error Code returned by the Delivery Transport',
        initialValue = 0,
    )
    errorString = schema.One(schema.String, initialValue = '')
    errorDate = schema.One(schema.DateTime)
    mailDelivery = schema.One(
        'MailDeliveryBase',
        displayName = u'Mail Delivery',
        doc = 'The Mail Delivery that cause this error',
        initialValue = None,
        inverse = 'deliveryErrors',
    )

    __default_path__ = MAIL_DEFAULT_PATH

    def __str__(self):
        if self.isStale():
            return super(MailDeliveryError, self).__str__()
            # Stale items shouldn't go through the code below

        return "| %d | %s | %s |" % (self.errorCode, self.errorString, str(self.errorDate))


class MailDeliveryBase(items.ContentItem):

    schema.kindInfo(
        displayName = u"Mail Delivery base kind",
        description =
            "Parent kind for delivery-specific attributes of a MailMessage"
    )

    mailMessage = schema.One(
        'MailMessageMixin',
        displayName = u'Message',
        doc = 'Message which this delivery item refers to',
        initialValue = None,
        inverse = 'deliveryExtension',
    )
    deliveryErrors = schema.Sequence(
        MailDeliveryError,
        displayName = u'Mail Delivery Errors',
        doc = 'Mail Delivery Errors associated with this transport',
        initialValue = [],
        inverse = MailDeliveryError.mailDelivery,
    )

    __default_path__ = MAIL_DEFAULT_PATH


class historyEnum(schema.Enumeration):
    values = "QUEUED", "FAILED", "SENT"

class stateEnum(schema.Enumeration):
    values = "DRAFT", "QUEUED", "SENT", "FAILED"


class SMTPDelivery(MailDeliveryBase):

    schema.kindInfo(
        displayName = u"SMTP Delivery",
        description = "Tracks the status of an outgoing message\n\n"
            "Issues:\n\n"
            "   Currently the parcel loader can't set a default value for the "
            "state attribute\n",
    )

    history = schema.Sequence(
        historyEnum,
        displayName = u'History',
        initialValue = [],
    )
    tries = schema.One(
        schema.Integer,
        displayName = u'Number of tries',
        doc = 'How many times we have tried to send it',
        initialValue = 0,
    )
    state = schema.One(
        stateEnum,
        displayName = u'State',
        doc = 'The current state of the message\n\n'
        "Issues:\n"
        "   We don't appear to be able to set an initialValue for an "
            "attribute whose enumeration is defined in the same file "
            "(a deficiency in the parcel loader)\n",
    )
   
    def __init__(self, name=None, parent=None, kind=None, view=None):
        super(SMTPDelivery, self).__init__(name, parent, kind, view)
        self.state = "DRAFT"

    def sendFailed(self):
        """
          Called from the Twisted thread to log errors in Send.
        """
        self.history.append("FAILED")
        self.state = "FAILED"

        self.tries += 1

    def sendSucceeded(self):
        """
          Called from the Twisted thread to log successes in Send.
        """
        self.history.append("SENT")
        self.state = "SENT"
        self.tries += 1


class IMAPDelivery(MailDeliveryBase):

    schema.kindInfo(
        displayName = u"IMAP Delivery",
        description = "Tracks the state of an inbound message",
    )

    folder = schema.One(
        schema.String, displayName = u'Folder', initialValue = '',
    )
    uid = schema.One(
        schema.Long,
        displayName = u'IMAP UID',
        doc = 'The unique IMAP ID for the message',
        initialValue = 0,
    )
    namespace = schema.One(
        schema.String,
        displayName = u'Namespace',
        doc = 'The namespace of the message',
        initialValue = '',
    )
    flags = schema.Sequence(
        schema.String, displayName = u'Flags', initialValue = [],
    )


class POPDelivery(MailDeliveryBase):

    schema.kindInfo(
        displayName = u"POP Delivery",
        description = "Tracks the state of an inbound message",
    )

    uid = schema.One(
        schema.String,
        displayName = u'POP UID',
        doc = 'The unique POP ID for the message',
        initialValue = '',
    )


class MIMEBase(items.ContentItem):
    schema.kindInfo(
        displayName=u"MIME Base Kind",
        description="Super kind for MailMessage and the various MIME kinds",
    )

    mimeType = schema.One(schema.String, initialValue = '')
    mimeContainer = schema.One(
        'MIMEContainer', initialValue = None, inverse = 'mimeParts',
    )

    schema.addClouds(
        sharing = schema.Cloud(mimeType),
    )

    __default_path__ = MAIL_DEFAULT_PATH


class MIMENote(MIMEBase):
    # @@@MOR This used to subclass notes.Note also, but since that superKind
    # was removed from MIMENote's superKinds list

    schema.kindInfo(
        displayName=u"MIME Note",
        description="MIMEBase and Note, rolled into one",
    )

    filename = schema.One(
        schema.String, displayName = _(u'File name'), initialValue = '',
    )
    filesize = schema.One(schema.Long, displayName = _(u'File Size'))

    schema.addClouds(
        sharing = schema.Cloud(filename, filesize),
    )


class MIMEContainer(MIMEBase):

    schema.kindInfo(displayName=u"MIME Container Kind")

    hasMimeParts = schema.One(schema.Boolean, initialValue = False)
    mimeParts = schema.Sequence(
        MIMEBase,
        displayName = u'MIME Parts',
        initialValue = [],
        inverse = MIMEBase.mimeContainer,
    )
    schema.addClouds(sharing = schema.Cloud(hasMimeParts, mimeParts))


class MailMessageMixin(MIMEContainer):
    """
    MailMessageMixin is the bag of Message-specific attributes.

    Used to mixin mail message attributes into a content item.

    Issues:
      - Once we have attributes and a cloud defined for Attachment, 
        we need to include attachments by cloud, and not by value.
      - Really not sure what to do with the 'downloadAccount' attribute 
        and how it should be included in the cloud.  For now it's byValue.
    """
    schema.kindInfo(
        displayName=u"Mail Message Mixin"
    )
    deliveryExtension = schema.One(
        MailDeliveryBase,
        initialValue = None,
        inverse = MailDeliveryBase.mailMessage,
    )
    isOutbound = schema.One(schema.Boolean, initialValue = False)
    isInbound = schema.One(schema.Boolean, initialValue = False)
    parentAccount = schema.One(
        AccountBase, initialValue = None, inverse = AccountBase.mailMessages,
    )
    spamScore = schema.One(schema.Float, initialValue = 0.0)
    rfc2822Message = schema.One(schema.Lob)
    dateSentString = schema.One(schema.String, initialValue = '')
    dateSent = schema.One(schema.DateTime, displayName=_(u"date sent"))
    messageId = schema.One(schema.String, initialValue = '')
    toAddress = schema.Sequence(
        'EmailAddress',
        displayName = _(u'To'),
        initialValue = [],
        inverse = 'messagesTo',
    )
    fromAddress = schema.One(
        'EmailAddress',
        displayName = _(u'From'),
        initialValue = None,
        inverse = 'messagesFrom',
    )
    replyToAddress = schema.One(
        'EmailAddress', initialValue = None, inverse = 'messagesReplyTo',
    )
    bccAddress = schema.Sequence(
        'EmailAddress', initialValue = [], inverse = 'messagesBcc',
    )
    ccAddress = schema.Sequence(
        'EmailAddress', initialValue = [], inverse = 'messagesCc',
    )
    subject = schema.One(schema.String, displayName=_(u"subject"))
    headers = schema.Mapping(
        schema.String, doc = 'Catch-all for headers', initialValue = {},
    )
    chandlerHeaders = schema.Mapping(schema.String, initialValue = {})
    who = schema.One(
        doc = "Redirector to 'toAddress'", redirectTo = 'toAddress',
    )
    whoFrom = schema.One(
        doc = "Redirector to 'fromAddress'", redirectTo = 'fromAddress',
    )
    about = schema.One(
        doc = "Redirector to 'subject'", redirectTo = 'subject',
    )
    date = schema.One(
        doc = "Redirector to 'dateSent'", redirectTo = 'dateSent',
    )

    mimeType = schema.One(schema.String, initialValue = 'message/rfc822')

    schema.addClouds(
        sharing = schema.Cloud(
            fromAddress, toAddress, ccAddress, bccAddress, replyToAddress,
            subject
        ),
        copying = schema.Cloud(
            fromAddress, toAddress, ccAddress, bccAddress, replyToAddress,
            byCloud = [MIMEContainer.mimeParts]
        ),
    )

    def InitOutgoingAttributes(self):
        """ Init any attributes on ourself that are appropriate for
        a new outgoing item.
        """
        try:
            super(MailMessageMixin, self).InitOutgoingAttributes()
        except AttributeError:
            pass
        MailMessageMixin._initMixin(self) # call our init, not the method of a subclass

    def _initMixin(self):
        """
          Init only the attributes specific to this mixin.
        Called when stamping adds these attributes, and from __init__ above.
        """
        # default the fromAddress to "me"
        self.fromAddress = EmailAddress.getCurrentMeEmailAddress(self.itsView)

        # default the subject to any super class "about" definition
        try:
            self.subject = self.getAnyAbout()
        except AttributeError:
            pass

        #self.outgoingMessage() # default to outgoing message
        self.isOutbound = True

    def getAnyAbout(self):
        """
        Get any non-empty definition for the "about" attribute.
        """
        try:
            # don't bother returning our default: an empty string 
            if self.subject:
                return self.subject

        except AttributeError:
            pass
        return super(MailMessageMixin, self).getAnyAbout()

    def outgoingMessage(self, account, type='SMTP'):
        assert type == "SMTP", "Only SMTP currently supported"

        assert isinstance(account, SMTPAccount)

        if self.deliveryExtension is None:
            self.deliveryExtension = SMTPDelivery(view=self.itsView)

        self.isOutbound = True
        self.parentAccount = account

    def incomingMessage(self, account, type="IMAP"):
        assert isinstance(account, DownloadAccountBase)

        if self.deliveryExtension is None:
            if type == "IMAP":
                 self.deliveryExtension = IMAPDelivery(view=self.itsView)
            elif type == "POP":
                 self.deliveryExtension = POPDelivery(view=self.itsView)

        self.isInbound = True
        self.parentAccount = account

    def getAttachments(self):
        """ First pass at API will be expanded upon later """
        return self.mimeParts

    def getNumberOfAttachments(self):
        """ First pass at API will be expanded upon later """
        return len(self.mimeParts)

    def hasAttachments(self):
        """ First pass at API will be expanded upon later """
        return self.hasMimeParts


    def shareSend(self):
        """
        Share this item, or Send if it's an Email
        We assume we want to send this MailMessage here.
        """
        # message the main view to do the work
        Globals.views[0].postEventByName('SendMail', {'item': self})

    def getSendability(self, ignoreAttr=None):
        """
        Return whether this item is ready to send: 'sendable', 'sent', 
        or 'not'. if ignoreAttr is specified, don't verify that value (because
        it's being edited in the UI and is known to be valid, and will get
        saved before sending).
        """
        # Not outbound? 
        if not self.isOutbound:
            return 'not'
        
        # Already sent?
        try:
            sent = self.deliveryExtension.state == "SENT"
        except AttributeError:
            sent = False
        if sent:
            return 'sent'
        
        # Addressed?
        # (This test will get more complicated when we add cc, bcc, etc.)
        sendable = ((ignoreAttr == 'toAddress' or len(self.toAddress) > 0) and
                    (ignoreAttr == 'fromAddress' or self.fromAddress is not None))
        return sendable and 'sendable' or 'not'

class MailMessage(MailMessageMixin, notes.Note):
    schema.kindInfo(
        displayName = _(u"Mail Message"),
        displayAttribute = "subject",
        description = "MailMessageMixin, and Note, all rolled up into one",
    )


class MIMEBinary(MIMENote):

    schema.kindInfo(displayName = u"MIME Binary Kind")


class MIMEText(MIMENote):

    schema.kindInfo(displayName = u"MIME Text Kind")

    charset = schema.One(
        schema.String,
        displayName = u'Character set encoding',
        initialValue = 'utf-8',
    )
    lang = schema.One(
        schema.String,
        displayName = u'Character set Language',
        initialValue = 'en',
    )


class MIMESecurity(MIMEContainer):

    schema.kindInfo(displayName=u"MIME Security Kind")


class EmailAddress(items.ContentItem):

    schema.kindInfo(
        displayName = u"Email Address Kind",
        displayAttribute = "emailAddress",
        description = "An item that represents a simple email address, plus "
                      "all the info we might want to associate with it, like "
                      "lists of message to and from this address.\n\n"
            "Example: abe@osafoundation.org\n\n"
            "Issues:\n"
            "   Someday we might want to have other attributes.  One example "
            "might be an 'is operational' flag that tells whether this "
            "address is still in service, or whether mail to this has been "
            "bouncing lately. Another example might be a 'superceded by' "
            "attribute, which would point to another Email Address item.\n"

            "   Depending on how we end up using the 'emailAddress' attribute, "
            "we might want to break it into two attributes, one for the 'Abe "
            "Lincoln' part, and one for the 'abe@osafoundation.org' part. "
            "Alternatively, we might want to use one of Andi's compound "
            "types, with two fields.\n",
    )

    emailAddress = schema.One(
        schema.String,
        displayName = _(u'Email Address'),
        doc = 'An RFC 822 email address.\n\n'
            "Examples:\n"
            '   "abe@osafoundation.org"\n'
            '   "Abe Lincoln {abe@osafoundation.org}" (except with ;angle '
                'brackets instead of \'{\' and \'}\')\n',
        initialValue = '',
    )
    fullName = schema.One(
        schema.String,
        displayName = _(u'Full Name'),
        doc = 'A first and last name associated with this email address',
        initialValue = '',
    )
    vcardType = schema.One(
        schema.String,
        displayName = u'vCard type',
        doc = "Typical vCard types are values like 'internet', 'x400', and "
              "'pref'. Chandler will use this attribute when doing "
              "import/export of Contact records in vCard format.",
        initialValue = '',
    )
    accounts = schema.Sequence(
        DownloadAccountBase,
        displayName = u'Used as Return Address by Email Account',
        doc = 'A list of Email Accounts that use this Email Address as the '
              'reply address for mail sent from the account.',
        initialValue = [],
        inverse = DownloadAccountBase.replyToAddress,
    )
    messagesBcc = schema.Sequence(
        MailMessageMixin,
        displayName = u'Messages Bcc',
        doc = 'A list of messages with their Bcc: header referring to this address',
        initialValue = [],
        inverse = MailMessageMixin.bccAddress,
    )
    messagesCc = schema.Sequence(
        MailMessageMixin,
        displayName = u'Messages cc',
        doc = 'A list of messages with their cc: header referring to this address',
        initialValue = [],
        inverse = MailMessageMixin.ccAddress,
    )
    messagesFrom = schema.Sequence(
        MailMessageMixin,
        displayName = u'Messages From',
        doc = 'A list of messages with their From: header referring to this address',
        initialValue = [],
        inverse = MailMessageMixin.fromAddress,
    )
    messagesReplyTo = schema.Sequence(
        MailMessageMixin,
        displayName = u'Messages Reply To',
        doc = 'A list of messages with their Reply-To: header referring to this address',
        initialValue = [],
        inverse = MailMessageMixin.replyToAddress,
    )
    messagesTo = schema.Sequence(
        MailMessageMixin,
        displayName = u'Messages To',
        doc = 'A list of messages with their To: header referring to this address',
        initialValue = [],
        inverse = MailMessageMixin.toAddress,
    )
    inviteeOf = schema.Sequence(
        'osaf.pim.collections.AbstractCollection',
        displayName = u'Invitee Of',
        doc = 'List of collections that the user is about to be invited to share with.',
        inverse = 'invitees',
    )

    schema.addClouds(
        sharing = schema.Cloud(emailAddress, fullName)
    )

    __default_path__ = MAIL_DEFAULT_PATH

    def __init__(self, name=None, parent=None, kind=None, view=None,
        clone=None, **kw
    ):
        super(EmailAddress, self).__init__(name, parent, kind, view, **kw)

        # copy the attributes if a clone was supplied
        if clone is not None:
            try:
                self.emailAddress = clone.emailAddress[:]
            except AttributeError:
                pass
            try:
                self.fullName = clone.fullName[:]
            except AttributeError:
                pass

    def __str__(self):
        if self.isStale():
            return super(EmailAddress, self).__str__()

        return self.__unicode__().encode('utf8')

    def __unicode__(self):
        """
          User readable string version of this address
        """
        if self.isStale():
            return super(EmailAddress, self).__unicode__()
            # Stale items shouldn't go through the code below

        try:
            if self is self.getCurrentMeEmailAddress(self.itsView):
                fullName = messages.ME
            else:
                fullName = self.fullName
        except AttributeError:
            fullName = u''

        if fullName is not None and len(fullName) > 0:
            if self.emailAddress:
                return fullName + u' <' + self.emailAddress + u'>'
            else:
                return fullName
        else:
            return self.getItemDisplayName()

        """
        Factory Methods
        --------------
        When creating a new EmailAddress, we check for an existing item first.
        We do look them up in the repository to prevent duplicates, but there's
        nothing to keep bad ones from accumulating, although repository
        garbage collection should eventually remove them.
        The "me" entity is used for Items created by the user, and it
        gets a reasonable emailaddress filled in when a send is done.
        This code needs to be reworked!
        """

    @classmethod
    def getEmailAddress(cls, view, nameOrAddressString, fullName=''):
        """
        Lookup or create an EmailAddress based on the supplied string.

        If a matching EmailAddress object is found in the repository, it
        is returned.  If there is no match, then a new item is created
        and returned.

        There are two ways to call this method:
          1. with something the user typed in nameOrAddressString, which
             will be parsed, and no fullName is needed
          2. with an plain email address in the nameOrAddressString, and a
             full name in the fullName field
             
        If a match is found for both name and address then it will be used.
        
        If there is no name specified, a match on address will be returned.
        
        If there is no address specified, a match on name will be returned.
        
        If both name and address are specified, but there's no entry that
        matches both, then a new entry is created.
        
        @param nameOrAddressString: emailAddress string, or fullName for lookup,
        or both in the form "name <address>"
        @type nameOrAddressString: C{String}
        @param fullName: optional explict fullName when not using the
        "name <address>" form of the nameOrAddressString parameter
        @type fullName: C{String}
        @return: C{EmailAddress} or None if not found, and nameOrAddressString is\
        not a valid email address.
        """
        # @@@DLD remove when we better sort out creation of "me" address w/o an account setup
        if nameOrAddressString is None:
            nameOrAddressString = u''

        # strip the address string of whitespace and question marks
        address = nameOrAddressString.strip ().strip(u'?')

        # check for "me"
        if address == messages.ME:
            return cls.getCurrentMeEmailAddress(view)

        # if no fullName specified, parse apart the name and address if we can
        if fullName != u'':
            name = fullName
        else:
            try:
                address.index(u'<')
            except ValueError:
                name = address
            else:
                name, address = address.split(u'<')
                address = address.strip(u'>').strip()
                name = name.strip()
                # ignore a name of "me"
                if name == messages.ME:
                    name = u''

        # check if the address looks like a valid emailAddress
        isValidAddress = cls.isValidEmailAddress(address)
        if not isValidAddress:
            address = None

        """
        At this point we should have:
            name - the name to search for, or ''
            address - the address to search for, or None
        If the user specified a single word which could also be a valid
        email address, we could have that word in both the address and
        name variables.
        """
        # @@@DLD - switch on the better queries
        # Need to override compare operators to use emailAddressesAreEqual, 
        #  deal with name=='' cases, name case sensitivity, etc

        addresses = []
        for candidate in EmailAddress.iterItems(view):
            if isValidAddress:
                if cls.emailAddressesAreEqual(candidate.emailAddress, address):
                    # found an existing address!
                    addresses.append(candidate)
            elif name != u'' and name == candidate.fullName:
                # full name match
                addresses.append(candidate)

        # process the result(s)
        # Hope for a match of both name and address
        # fall back on a match of the address, then name
        addressMatch = None
        nameMatch = None
        for candidate in addresses:
            if isValidAddress:
                if cls.emailAddressesAreEqual(candidate.emailAddress, address):
                    # found an existing address match
                    addressMatch = candidate
            if name != u'' and name == candidate.fullName:
                # full name match
                nameMatch = candidate
                if addressMatch is not None:
                    # matched both
                    return addressMatch
        else:
            # no double-matches found
            if name == address:
                name = u''
            if addressMatch is not None and name == u'':
                return addressMatch
            if nameMatch is not None and address is None:
                return nameMatch
            if isValidAddress:
                # make a new EmailAddress
                newAddress = EmailAddress(view=view)
                newAddress.emailAddress = address
                newAddress.fullName = name
                return newAddress
            else:
                return None

    @classmethod
    def format(cls, emailAddress):
        assert isinstance(emailAddress, EmailAddress), "You must pass an EmailAddress Object"

        if emailAddress.fullName is not None and len(emailAddress.fullName.strip()) > 0:
            return emailAddress.fullName + u" <" + emailAddress.emailAddress + u">"

        return emailAddress.emailAddress

    @classmethod
    def isValidEmailAddress(cls, emailAddress):
        """
        This method tests an email address for valid syntax as defined RFC 822.
        The method validates addresses in the form 'John Jones <john@test.com>'
        and 'john@test.com'

        @param emailAddress: A string containing a email address to validate.
        @type addr: C{String}
        @return: C{Boolean}
        """

        assert isinstance(emailAddress, (str, unicode)), "Email Address must be in string or unicode format"

        #XXX: Strip any name information. i.e. John test <john@test.com>`from the email address
        emailAddress = Utils.parseaddr(emailAddress)[1]

        return re.match("^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$", emailAddress) is not None

    @classmethod
    def parseEmailAddresses(cls, view, addressesString):
        """
        Parse the email addresses in addressesString and return
        a tuple with: (the processed string, a list of EmailAddress
        items created/found for those addresses, the number of 
        invalid addresses we found).
        """
        # If we got nothing or whitespace, return it as-is.
        if len(addressesString.strip()) == 0:
            return (addressesString, [], 0)
        
        validAddresses = []
        processedAddresses = []
        invalidCount = 0

        # get the user's address strings into a list; tolerate
        # commas or semicolons as separators
        addresses = [ address.strip() for address in \
                      addressesString.replace('?','').replace(';', ',').split(',') ]

        # build a list of all processed addresses, and all valid addresses
        for address in addresses:
            ea = EmailAddress.getEmailAddress(view, address)
            if ea is None:
                processedAddresses.append(address + '?')
                invalidCount += 1
            else:
                processedAddresses.append(unicode(ea))
                validAddresses.append(ea)

        # prepare the processed addresses return value
        processedResultString = ', '.join (processedAddresses)
        return (processedResultString, validAddresses, invalidCount)
    
    @classmethod
    def emailAddressesAreEqual(cls, emailAddressOne, emailAddressTwo):
        """
        This method tests whether two email addresses are the same.
        Addresses can be in the form john@jones.com or John Jones <john@jones.com>.
        The method strips off the username and <> brakets if they exist and just compares
        the actual email addresses for equality. It will not look to see if each
        address is RFC 822 compliant only that the strings match. Use C{EmailAddress.isValidEmailAddress}
        to test for validity.

        @param emailAddressOne: A string containing a email address to compare.
        @type emailAddressOne: C{String}
        @param emailAddressTwo: A string containing a email address to compare.
        @type emailAddressTwo: C{String}
        @return: C{Boolean}
        """
        assert isinstance(emailAddressOne, (str, unicode))
        assert isinstance(emailAddressTwo, (str, unicode))

        emailAddressOne = Utils.parseaddr(emailAddressOne)[1]
        emailAddressTwo = Utils.parseaddr(emailAddressTwo)[1]

        return emailAddressOne.lower() == emailAddressTwo.lower()


    @classmethod
    def getCurrentMeEmailAddress(cls, view):
        """
          Lookup the "me" EmailAddress.
        The "me" EmailAddress is whichever entry is the current IMAP default
        address.
        """

        account = getCurrentMailAccount(view)

        if account is not None and hasattr(account, 'replyToAddress'):
            return account.replyToAddress

        return None


# Map from account type strings to account types

ACCOUNT_TYPES = {
    'POP': POPAccount,
    'SMTP': SMTPAccount,
    'IMAP': IMAPAccount,
}
