__version__ = "$Revision$"
__date__ = "$Date$"
__copyright__ = "Copyright (c) 2005 Open Source Applications Foundation"
__license__ = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

__all__ = [
    'ChandlerServerHandle',
    'checkAccess',
    'CANT_CONNECT',
    'NO_ACCESS',
    'READ_ONLY',
    'READ_WRITE',
    'IGNORE',
]

import zanshin.webdav
import zanshin.util

import M2Crypto.BIO
import M2Crypto.SSL.Checker
import chandlerdb
import twisted.internet.error as error
from twisted.internet import reactor

import application.Globals as Globals
import application.Utility as Utility
from osaf.framework.certstore import ssl
                

class ChandlerServerHandle(zanshin.webdav.ServerHandle):
    def __init__(self, host=None, port=None, username=None, password=None,
                 useSSL=False, repositoryView=None):
        
        self.resourcesByPath = {}   # Caches resources indexed by path

        self.factory = ChandlerHTTPClientFactory()
        self.factory.protocol = zanshin.webdav.WebDAVProtocol
        self.factory.startTLS = useSSL
        self.factory.host = host
        self.factory.port = port
        self.factory.username = username
        self.factory.password = password
        self.factory.retries = zanshin.webdav.DEFAULT_RETRIES
        self.factory.repositoryView = repositoryView

        #self.factory.extraHeaders = { 'Connection' : "close" }
        self.factory.logging = True

    def blockUntil(self, callable, *args, **keywds):
        # Since there can be several errors in a connection, we must keep 
        # trying until we either get a successful connection or the user 
        # decides to cancel/disconnect, or there is an error we don't know 
        # how to deal with.
        while True:
            try:
                return zanshin.util.blockUntil(callable, *args, **keywds)
            except Utility.CertificateVerificationError, err:
                assert err.args[1] == 'certificate verify failed'
    
                # Reason why verification failed is stored in err.args[0], see
                # codes at http://www.openssl.org/docs/apps/verify.html#DIAGNOSTICS
    
                retry = (lambda: setattr(self, '_retry', True))
    
                if err.args[0] in ssl.unknown_issuer:
                    handler = lambda: \
                        Globals.views[0].askTrustSiteCertificate(err.untrustedCertificates[0], retry)
                else:
                    handler = lambda: \
                        Globals.views[0].askIgnoreSSLError(err.untrustedCertificates[0], err.args[0], retry)
    
                self._handleSSLError(handler, err, callable, *args, **keywds)
                        
            except M2Crypto.SSL.Checker.WrongHost, err:
                retry = (lambda: setattr(self, '_retry', True))
    
                handler = lambda: \
                    Globals.views[0].askIgnoreSSLError(err.pem, 
                                                       str(err), # XXX intl
                                                       retry)
                self._handleSSLError(handler, err, callable, *args, **keywds)
    
            except M2Crypto.BIO.BIOError, error:
                # Translate the mysterious M2Crypto.BIO.BIOError
                raise error.SSLError(error)

    def _handleSSLError(self, handler, err, callable, *args, **keywds):
        self._reconnect = False

        if Globals.wxApplication is not None: # test framework has no wxApplication
            handler()
            
        if hasattr(self, '_retry'):
            del self._retry
        else:
            raise err
        


class ChandlerHTTPClientFactory(zanshin.http.HTTPClientFactory):
    def _makeConnection(self, timeout):
        if self.logging:
            #_doLog("[Connecting to %s:%s]" % (self.host, self.port))
            pass
            
        if self.startTLS:
            result = ssl.connectSSL(self.host, self.port, self,
                                    self.repositoryView, timeout=timeout)
        else:
            result = reactor.connectTCP(self.host, self.port,
                                        self, timeout=timeout)
            
        self._active = result
        
        return result



# ----------------------------------------------------------------------------

CANT_CONNECT = -1
NO_ACCESS    = 0
READ_ONLY    = 1
READ_WRITE   = 2
IGNORE       = 3

def checkAccess(host, port=80, useSSL=False, username=None, password=None,
                path=None, repositoryView=None):
    """
    Check the permissions for a webdav account by reading and writing
    to that server.

    Returns a tuple (result code, reason), where result code indicates the
    level of permissions: CANT_CONNECT, NO_ACCESS, READ_ONLY, READ_WRITE.

    CANT_CONNECT will be accompanied by a "reason" string that was provided
    from the socket layer.
    
    NO_ACCESS and READ_ONLY will be accompanied by an HTTP status code.

    READ_WRITE will have a "reason" of None.
    """

    handle = ChandlerServerHandle(host=host, port=port, username=username,
                   password=password, useSSL=useSSL,
                   repositoryView=repositoryView)

    # Make sure path begins/ends with /
    path = path.strip("/")
    if path == "":
        path = "/"
    else:
        path = "/" + path + "/"

    # Get the C{Resource} object associated with the specified
    # path
    topLevelResource = handle.getResource(path)

    # Now, try to list all the child resources of the top level.
    # This may lead to auth errors (mistyped username/password)
    # or other failures (e.g., nonexistent path, mistyped
    # host).
    try:
        resourceList = handle.blockUntil(topLevelResource.propfind, depth=1)
    except zanshin.webdav.ConnectionError, err:
        return (CANT_CONNECT, err.message)
    except zanshin.webdav.WebDAVError, err:
        return (NO_ACCESS, err.status)
    except error.SSLError, err:
        return (CANT_CONNECT, err) # Unhandled SSL error
    except M2Crypto.SSL.Checker.WrongHost:
        return (IGNORE, None) # The user cancelled SSL error dialog
    except Utility.CertificateVerificationError:
        return (IGNORE, None) # The user cancelled trust cert/SSL error dialog
    except error.ConnectionDone, err:
        return (CANT_CONNECT, err)
    
    # Unique the child names returned by the server. (Note that
    # collection subresources will have a name that ends in '/').
    # We're doing this so that we can try a PUT below to a (hopefully
    # nonexistent) path.
    childNames = set([])
    
    for child in resourceList:
        if child is not topLevelResource:
            childPath = child.path
            if childPath and childPath[-1] == '/':
                childPath = childPath[:-1]
            childComponents = childPath.split('/')
            if len(childComponents):
                childNames.add(childComponents[-1])

    # Try to figure out a unique path (although the odds of
    # even more than one try being needs are probably negligible)..
    triesLeft = 10
    testFilename = unicode(chandlerdb.util.c.UUID())
    
    # Random string to use for trying a put
    while testFilename in childNames:
        triesLeft -= 1

        if triesLeft == 0:
            # @@@ [grant] This can't be right, but it's what was in the
            # original (pre-zanshin) code.
            return -1

        testFilename = chandlerdb.util.c.UUID()
    
    # Now, we try to PUT a small test file on the server. If that
    # fails, we're going to say the user only has read-only access.
    try:
        tmpResource = handle.blockUntil(topLevelResource.createFile,
                                testFilename, body='Write access test')
    except zanshin.webdav.WebDAVError, e:
        return (READ_ONLY, e.status)
        
    # Remove the temporary resource, and ignore failures (since there's
    # not much we can do here, anyway).
    try:
        handle.blockUntil(tmpResource.delete)
    except:
        pass
        
    # Success!
    return (READ_WRITE, None)
