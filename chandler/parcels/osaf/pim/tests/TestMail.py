"""
Unit tests for mail
"""

__copyright__ = "Copyright (c) 2003-2004 Open Source Applications Foundation"
__license__   = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

import unittest, os

import osaf.pim.tests.TestContentModel as TestContentModel
import osaf.pim.mail as Mail

from datetime import datetime
from repository.util.Path import Path
from PyICU import ICUtzinfo

class MailTest(TestContentModel.ContentModelTestCase):
    """ Test Mail Content Model """

    def testMail(self):
        """ Simple test for creating instances of email related kinds """

        self.loadParcel("osaf.pim.mail")


        # Test the globals
        mailPath = Path('//parcels/osaf/pim/mail')
        view = self.rep.view

        self.assertEqual(Mail.AccountBase.getKind(view),
                         view.find(Path(mailPath, 'AccountBase')))

        self.assertEqual(Mail.IMAPAccount.getKind(view),
                         view.find(Path(mailPath, 'IMAPAccount')))

        self.assertEqual(Mail.SMTPAccount.getKind(view),
                         view.find(Path(mailPath, 'SMTPAccount')))

        self.assertEqual(Mail.MailDeliveryError.getKind(view),
                         view.find(Path(mailPath, 'MailDeliveryError')))

        self.assertEqual(Mail.MailDeliveryBase.getKind(view),
                         view.find(Path(mailPath, 'MailDeliveryBase')))

        self.assertEqual(Mail.SMTPDelivery.getKind(view),
                         view.find(Path(mailPath, 'SMTPDelivery')))

        self.assertEqual(Mail.IMAPDelivery.getKind(view),
                         view.find(Path(mailPath, 'IMAPDelivery')))

        self.assertEqual(Mail.MIMEBase.getKind(view),
                         view.find(Path(mailPath, 'MIMEBase')))

        self.assertEqual(Mail.MIMENote.getKind(view),
                         view.find(Path(mailPath, 'MIMENote')))

        self.assertEqual(Mail.MailMessage.getKind(view),
                         view.find(Path(mailPath, 'MailMessage')))

        self.assertEqual(Mail.MailMessageMixin.getKind(view),
                         view.find(Path(mailPath, 'MailMessageMixin')))

        self.assertEqual(Mail.MIMEBinary.getKind(view),
                         view.find(Path(mailPath, 'MIMEBinary')))

        self.assertEqual(Mail.MIMEText.getKind(view),
                         view.find(Path(mailPath, 'MIMEText')))

        self.assertEqual(Mail.MIMEContainer.getKind(view),
                         view.find(Path(mailPath, 'MIMEContainer')))

        self.assertEqual(Mail.MIMESecurity.getKind(view),
                         view.find(Path(mailPath, 'MIMESecurity')))

        self.assertEqual(Mail.EmailAddress.getKind(view),
                         view.find(Path(mailPath, 'EmailAddress')))


        # Construct sample items
        accountBaseItem = Mail.AccountBase("accountBaseItem", itsView=view)
        imapAccountItem = Mail.IMAPAccount("imapAccountItem", itsView=view)
        smtpAccountItem = Mail.SMTPAccount("smtpAccountItem", itsView=view)
        mailDeliveryErrorItem = Mail.MailDeliveryError("mailDeliveryErrorItem",
                                                       itsView=view)
        mailDeliveryBaseItem = Mail.MailDeliveryBase("mailDeliveryBaseItem",
                                                     itsView=view)
        smtpDeliveryItem = Mail.SMTPDelivery("smtpDeliveryItem", itsView=view)
        imapDeliveryItem = Mail.IMAPDelivery("imapDeliveryItem", itsView=view)
        mimeBaseItem = Mail.MIMEBase("mimeBaseItem", itsView=view)
        mimeNoteItem = Mail.MIMENote("mimeNoteItem", itsView=view)
        mailMessageItem = Mail.MailMessage("mailMessageItem", itsView=view)
        mailMessageMixinItem = Mail.MailMessageMixin("mailMessageMixinItem",
                                                     itsView=view)
        mimeBinaryItem = Mail.MIMEBinary("mimeBinaryItem", itsView=view)
        mimeTextItem = Mail.MIMEText("mimeTextItem", itsView=view)
        mimeContainerItem = Mail.MIMEContainer("mimeContainerItem", itsView=view)
        mimeSecurityItem = Mail.MIMESecurity("mimeSecurityItem", itsView=view)
        emailAddressItem = Mail.EmailAddress("emailAddressItem", itsView=view)

        # Double check kinds
        self.assertEqual(accountBaseItem.itsKind,
                         Mail.AccountBase.getKind(view))

        self.assertEqual(imapAccountItem.itsKind,
                         Mail.IMAPAccount.getKind(view))

        self.assertEqual(smtpAccountItem.itsKind,
                         Mail.SMTPAccount.getKind(view))

        self.assertEqual(mailDeliveryErrorItem.itsKind,
                         Mail.MailDeliveryError.getKind(view))

        self.assertEqual(mailDeliveryBaseItem.itsKind,
                         Mail.MailDeliveryBase.getKind(view))

        self.assertEqual(smtpDeliveryItem.itsKind,
                         Mail.SMTPDelivery.getKind(view))

        self.assertEqual(imapDeliveryItem.itsKind,
                         Mail.IMAPDelivery.getKind(view))

        self.assertEqual(mimeBaseItem.itsKind,
                         Mail.MIMEBase.getKind(view))

        self.assertEqual(mimeNoteItem.itsKind,
                         Mail.MIMENote.getKind(view))

        self.assertEqual(mailMessageItem.itsKind,
                         Mail.MailMessage.getKind(view))

        self.assertEqual(mailMessageMixinItem.itsKind,
                         Mail.MailMessageMixin.getKind(view))

        self.assertEqual(mimeBinaryItem.itsKind,
                         Mail.MIMEBinary.getKind(view))

        self.assertEqual(mimeTextItem.itsKind,
                         Mail.MIMEText.getKind(view))

        self.assertEqual(mimeContainerItem.itsKind,
                         Mail.MIMEContainer.getKind(view))

        self.assertEqual(mimeSecurityItem.itsKind,
                         Mail.MIMESecurity.getKind(view))

        self.assertEqual(emailAddressItem.itsKind,
                         Mail.EmailAddress.getKind(view))

        accountBaseItem = self.__populateAccount(accountBaseItem)
        smtpAccountItem = self.__populateAccount(smtpAccountItem)
        imapAccountItem = self.__populateAccount(imapAccountItem)

        mailDeliveryErrorItem.errorCode = 25
        mailDeliveryErrorItem.errorString = u"Test String"
        mailDeliveryErrorItem.errorDate = datetime.now(ICUtzinfo.default)

        smtpDeliveryItem.state = "DRAFT"
        smtpDeliveryItem.deliveryError = mailDeliveryErrorItem
        imapDeliveryItem.uid = 0
        mimeBaseItem.mimeType = "SGML"
        mimeBinaryItem.mimeType = "APPLICATION"
        mimeTextItem.mimeType = "PLAIN"
        mimeContainerItem.mimeType = "ALTERNATIVE"
        mimeSecurityItem.mimeType = "SIGNED"

        # Literal properties
        mailMessageItem.dateSent = datetime.now(ICUtzinfo.default)
        mailMessageItem.dateReceived = datetime.now(ICUtzinfo.default)
        mailMessageItem.subject = u"Hello"
        mailMessageItem.spamScore = 5

        # Item Properties
        emailAddressItem.emailAddress = u"test@test.com"
        mailMessageItem.replyAddress = emailAddressItem

        self._reopenRepository()
        view = self.rep.view

        contentItemParent = view.findPath("//userdata")
        mailMessageItem = contentItemParent.getItemChild("mailMessageItem")

        #Test cloud membership

        items = mailMessageItem.getItemCloud('copying')
        self.assertEqual(len(items), 1)

    def __populateAccount(self, account):

        account.username = u"test"
        account.password = u"test"
        account.host = u"test"

        if type(account) == Mail.AccountBase:
            account.port = 1
            account.connectionSecurity = "NONE"

        if type(account) == Mail.SMTPAccount:
            account.fullName = u"test"
            account.replyToAddress = Mail.EmailAddress(itsView=account.itsView)
            account.replyToAddress.emailAddress = u"test@test.com"

if __name__ == "__main__":
    unittest.main()
