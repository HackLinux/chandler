__revision__  = "$Revision: 7664 $"
__date__      = "$Date: 2005-10-06 10:07:33 -1000 (Thu, 06 Oct 2005) $"
__copyright__ = "Copyright (c) 2004 Open Source Applications Foundation"
__license__   = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

""" Unit test for i18n message parsing """

import MailTestCase as MailTestCase
import osaf.mail.message as message
import unittest as unittest
import os, email


class MessageI18nTest(MailTestCase.MailTestCase):
    def testI18nMessage(self):
        """
           Basic unit test which loads a mail message
           in the utf-8 charset encoding off the filesystem
           and converts the bytes to a Chandler
           C{Mail.MailMessage}.
          
           This Chandler c{Mail.MailMessage} is then 
           converted back to bytes for sending.
           The bytes contained in the To, From, Subject,
           and Body payload are compared with the original.
           
           This test confirms that encoded headers
           are decoded to Unicode, The Body is converted
           from bytes to Unicode, and that the headers and
           Body are properly encoded back to bytes.
           
           A header in a non-ascii charset
           should be encoded for sending. For example:
               
           To: =?utf-8?b?IsSFxI3EmcSXxK/FocWzxavFviDEhMSMxJjElsSuxaDFssWqxb0i?= <testreceive@test.com>
        """
        
        msgText = self.__loadTestMessage()  
        
        #The message.messageObjectToKind method will
        #remove the headers from the c{email.Message} object
        #as they are encountered. Thus we want to keep a copy
        #of the original in mOne and pass mTmp to the 
        #messageObjectToKind method
        mTmp = email.message_from_string(msgText)
        mOne = email.message_from_string(msgText)    
        messageKind = message.messageObjectToKind(self.rep.view, mTmp, msgText)
        mTwo  = message.kindToMessageObject(messageKind)

        self.assertEquals(mOne['To'], mTwo['To'])
        self.assertEquals(mOne['From'], mTwo['From'])
        self.assertEquals(mOne['Subject'], mTwo['Subject'])
        self.assertEquals(mOne.get_payload(), mTwo.get_payload())
        
    def __loadTestMessage(self):
        rootdir = os.environ['CHANDLERHOME']
        testMessage = os.path.join(rootdir, 'parcels', 'osaf', 'mail',
                                   'tests', 'i18n_tests', 'test_i18n_utf8')

        fp = open(testMessage)
        messageText = fp.read()
        fp.close()
        
        return messageText
    
    def setUp(self):
        super(MessageI18nTest, self).setUp()
        self.loadParcel("osaf.pim.mail")
       

if __name__ == "__main__":
   unittest.main()
