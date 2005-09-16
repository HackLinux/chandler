"""
Certificate store  and SSL dialogs

@copyright: Copyright (c) 2005 Open Source Applications Foundation
@license:   http://osafoundation.org/Chandler_0.1_license_terms.htm
"""
__parcel__ = "osaf.framework.certstore"

import logging

import wx

from i18n import OSAFMessageFactory as _
from osaf import messages
from osaf.framework.certstore import utils, errors

log = logging.getLogger(__name__)

class ImportCertificateDialog(wx.Dialog):
    def __init__(self, parent, type, x509, choices, size=wx.DefaultSize,
     pos=wx.DefaultPosition, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER):
        """
        Ask the user if they would like to import and trust a certificate.
        
        @param type: Certificate type
        @param x509: The certificate to import.
        @param choices: List of possible trust values.
        """ 

        # Instead of calling wx.Dialog.__init__ we precreate the dialog
        # so we can set an extra style that must be set before
        # creation, and then we create the GUI dialog using the Create
        # method.
        pre = wx.PreDialog()
        pre.Create(parent, -1, _(u'Import certificate?'), pos, size, style)

        # This next step is the most important, it turns this Python
        # object into the real wrapper of the dialog (instead of pre)
        # as far as the wxPython extension is concerned.
        self.this = pre.this

        # Now continue with the normal construction of the dialog
        # contents
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Static text

        message = _(u'Do you want to import this certificate?\nType: %(certType)s\nSHA1 fingerprint: %(fingerprint)s') % {'certType': type, 'fingerprint': certificate.fingerprint(x509)}
        label = wx.StaticText(self, -1, message)
        sizer.Add(label, 0, wx.ALIGN_LEFT|wx.ALL, 5)

        # multiline readonly edit control
        
        text = wx.TextCtrl(self, -1, x509.as_text(), wx.DefaultPosition, 
                           [400,-1], style=wx.TE_MULTILINE|wx.TE_READONLY)
        sizer.Add(text, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)

        # checkboxes
        
        choicebox = wx.BoxSizer(wx.VERTICAL)
        
        cs = []
        for choice in choices:
            cb = wx.CheckBox(self, -1, choice, wx.DefaultPosition, 
                             wx.DefaultSize, style=wx.ALIGN_LEFT)
            cs += [cb]
            choicebox.Add(cb, 1, wx.ALIGN_LEFT|wx.ALL, 5)

        sizer.Add(choicebox, 0, wx.ALIGN_LEFT|wx.ALL, 5)

        # OK, Cancel buttons

        box = wx.BoxSizer(wx.HORIZONTAL)

        btn = wx.Button(self, wx.ID_OK, u" " +  messages.OK + u" ")
        box.Add(btn, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        btn = wx.Button(self, wx.ID_CANCEL, u" " + messages.CANCEL + u" ")
        btn.SetDefault()
        box.Add(btn, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        sizer.Add(box, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        self.SetSizer(sizer)
        self.SetAutoLayout(True)
        sizer.Fit(self)

        self.cs = cs
        
    def GetSelections(self):
        sel = []
        index = 0
        for cb in self.cs:
            if cb.IsChecked():
                sel += [index]
            index += 1

        return sel


class TrustSiteCertificateDialog(wx.Dialog):
    """
    This is the dialog we show to users when the certificate returned by the
    server is signed by a certificate authority that is unknown to us. The user
    has the option of adding the server certificate to a list of trusted
    certificates either permanently or until program exit.
    """
    
    def __init__(self, parent, x509, size=wx.DefaultSize,
     pos=wx.DefaultPosition, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER):
        """
        Initialize dialog.

        @param x509: The certificate the site returned.
        """ 

        # Instead of calling wx.Dialog.__init__ we precreate the dialog
        # so we can set an extra style that must be set before
        # creation, and then we create the GUI dialog using the Create
        # method.
        pre = wx.PreDialog()
        pre.Create(parent, -1, _(u'Trust site certificate?'), pos, size, style)

        # This next step is the most important, it turns this Python
        # object into the real wrapper of the dialog (instead of pre)
        # as far as the wxPython extension is concerned.
        self.this = pre.this

        # Now continue with the normal construction of the dialog
        # contents
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Static text

        message = _(u'Do you want to trust this certificate?\nSHA1 fingerprint: %s') % utils.fingerprint(x509)
        label = wx.StaticText(self, -1, message)
        sizer.Add(label, 0, wx.ALIGN_LEFT|wx.ALL, 5)

        # multiline readonly edit control
        
        text = wx.TextCtrl(self, -1, x509.as_text(), wx.DefaultPosition, 
                           [400,-1], style=wx.TE_MULTILINE|wx.TE_READONLY)
        sizer.Add(text, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)

        # radio
        
        radiobox = wx.BoxSizer(wx.VERTICAL)
        
        first = True
        rbs = []
        choices=[_(u'Trust the authenticity of this certificate until program exit.'),
                 _(u'Trust the authenticity of this certificate permanently.')]
        for choice in choices:
            if first:
                style = wx.ALIGN_LEFT|wx.RB_GROUP
            else:
                style = wx.ALIGN_LEFT
            rb = wx.RadioButton(self, -1, choice, wx.DefaultPosition, 
                                wx.DefaultSize, style)
            rbs += [rb]
            radiobox.Add(rb, 1, wx.ALIGN_LEFT|wx.ALL, 5)
            
            if first:
                rb.SetValue(True)
                first = False

        sizer.Add(radiobox, 0, wx.ALIGN_LEFT|wx.ALL, 5)

        # OK, Cancel buttons

        box = wx.BoxSizer(wx.HORIZONTAL)

        btn = wx.Button(self, wx.ID_OK, messages.OK_BUTTON)
        box.Add(btn, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        btn = wx.Button(self, wx.ID_CANCEL, messages.CANCEL_BUTTON)
        btn.SetDefault()
        box.Add(btn, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        sizer.Add(box, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        self.SetSizer(sizer)
        self.SetAutoLayout(True)
        sizer.Fit(self)

        self.rbs = rbs

    def GetSelection(self):
        """
        Returns the zero-based index of the selected radio button.
        """
        sel = 0
        for rb in self.rbs:
            if rb.GetValue():
                return sel
            sel += 1
            

class IgnoreSSLErrorDialog(wx.Dialog):
    """
    This is the dialog we show to users when the there are errors with the
    SSL connection. There can be zero or more certificate validation errors,
    and a post connection check failure which indicates the certificate as
    issued for another server. The user can ignore the specific error with
    the specific certificate until program exit and connect, or cancle. Note
    that any of these errors can potentially be active hacking attempts, so
    unless the user is knowledgeable they can subject themselves to attacks
    by choosing to ignore errors.
    """

    def __init__(self, parent, x509, err, size=wx.DefaultSize,
     pos=wx.DefaultPosition, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER):
        """
        Initialize dialog.

        @param x509: The certificate the site returned.
        @param err:  The verification error code
        """ 

        # Instead of calling wx.Dialog.__init__ we precreate the dialog
        # so we can set an extra style that must be set before
        # creation, and then we create the GUI dialog using the Create
        # method.
        pre = wx.PreDialog()
        pre.Create(parent, -1, _(u'Ignore SSL error?'), pos, size, style)

        # This next step is the most important, it turns this Python
        # object into the real wrapper of the dialog (instead of pre)
        # as far as the wxPython extension is concerned.
        self.this = pre.this

        # Now continue with the normal construction of the dialog
        # contents
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Static text

        try:
            err.upper()
            errString = err
        except AttributeError:
            errString = errors.getCertificateVerifyErrorString(err)
        message = _(u'There was an error with this SSL connection.\nThe error was: %s.\nIgnoring this error may be dangerous!\nSHA1 fingerprint: %s') % (errString, utils.fingerprint(x509))
        label = wx.StaticText(self, -1, message)
        sizer.Add(label, 0, wx.ALIGN_LEFT|wx.ALL, 5)

        # multiline readonly edit control
        
        text = wx.TextCtrl(self, -1, x509.as_text(), wx.DefaultPosition, 
                           [400,-1], style=wx.TE_MULTILINE|wx.TE_READONLY)
        sizer.Add(text, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)

        # OK, Cancel buttons

        box = wx.BoxSizer(wx.HORIZONTAL)

        btn = wx.Button(self, wx.ID_OK, _(u'Ignore this error'))
        box.Add(btn, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        btn = wx.Button(self, wx.ID_CANCEL, _(u'Disconnect'))
        btn.SetDefault()
        box.Add(btn, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        sizer.Add(box, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        self.SetSizer(sizer)
        self.SetAutoLayout(True)
        sizer.Fit(self)
