__version__ = "$Revision$"
__date__ = "$Date$"
__copyright__ = "Copyright (c) 2003-2004 Open Source Applications Foundation"
__license__ = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

import wx
import application.Globals as Globals

"""
Overview of Drag and Drop:
==========================

Mixin Classes
-------------
Mixin classes are provided that should be mixed in to your widget class:
    - Use DraggableWidget for things that export data through Drag & Drop.
    - Use DropReceiveWidget for things that import data through Drag & Drop.
    - Use one of the ClipboardDataHandlers to handle copying data from a
            widget or pasting data into a widget.
        - TextClipboardHandler handles Text data with EditText widgets
        - ItemClipboardHandler handles Item data, with help from the Content Model

Clipboard Handlers
------------------
Since most of Chandler data are Items, most widgets will use the ItemClipboardHandler.

Widgets that mix in ItemClipboardHandler should implement:
    - SelectedItems() to return a list of items currently selected (Copy, Drag)
    - AddItems() to insert a list of items (Paste, Drop)
    - DeleteSelection() to remove the selected items (Cut, Move)

It's easy to write new ClipboardHandlers for your own kind of data:
    - CopyData() - gather data from your widget into a DataObject
    - PasteData() - place data from a DataObject into your widget
    - ClipboardDataFormat() - define the format of your DataObject
    - ClipboardDataObject() - create your data object
    - CanCopy(), CanCut(), CanPaste() - return booleans
    - Cut(), Copy(), Paste() - interact with the clipboard calling 
        CopyData() or PasteData().

What's going on inside
----------------------
wxWidgets level:
    - wx.DropSource - the window you are dragging from
    - wx.DropTarget - the window you are dragging to
    - wx.DataObject - the stuff being dragged
    - wx.DataFormat - the format of the DataObject
   
CPIA level:
    - DraggableWidget - class to mixin that makes widget a DropSource
    - DropReceiveWidget - class to mixin to make a widget a DropTarget
    - _DropTarget - helper object connected to the DropReceiveWidget
       that converts wxWidget callbacks to CPIA DnD callbacks.
   
"""

# Global to remember the widget we dragged from
DraggedFromWidget = None

class DraggableWidget (object):
    """
    Mixin class for widgets with data that are draggable.
    """
    def DoDragAndDrop(self, copyOnly=None):
        """
        Do a Drag And Drop operation, given the data in the selection.
        If you want to disable Move, pass True for copyOnly.  Passing
           False allows the Move.  Passing None (the default) will
           allow the Move iff you have a DeleteSelection method.
        @param copyOnly: flag to disable a move operation
        @type copyOnly: C{None} to allow a move based on the presence of a Delete capability
            C{True} to disallow a move
            C{False} to allow a move
        @return: C{wx.DragResult} - e.g. wx.DragNone if the drag was refused
        """
        global DraggedFromWidget
        # make sure we got mixed in OK, so the __init__ got called.
        if __debug__:
            assert self.clipboardHandlerInited, "Object of type %s never inited its ClipboardHandler" % type(self)

        # set up copyOnly flag - so we know if a 'move' is allowed
        if copyOnly is None:
            if not hasattr (self, 'DeleteSelection'):
                copyOnly = True
            else:
                copyOnly = False

        # Flags of copy-only will disallow the move, giving the wrong cursor
        #  until the user presses the option key - not good.
        # We'll map move to copy during the drag instead.
        flags = wx.Drag_AllowMove

        # create the drop source, set up its data
        DraggedFromWidget = self
        self.copyOnly = copyOnly
        self.dropSource = DropSourceWithFeedback(self)
        self.dataObject = self.CopyData()
        self.dropSource.SetData(self.dataObject)

        # drag and drop the DropSource.  Many callbacks happen here.
        result = self.dropSource.DoDragDrop(flags=flags)
        if not getattr(self, 'dropResult', True):  # workaround for bug 4128:
            result = wx.DragNone # override the result

        # if we moved the item, instead of the usual copy, remove the original
        if not copyOnly and result == wx.DragMove:
            self.DeleteSelection()
        DraggedFromWidget = None
        return result

class DropReceiveWidget (object):
    """
    Mixin class for widgets that want to receive drag and drop events.
    """
    def __init__(self, *arguments, **keywords):
        super (DropReceiveWidget, self).__init__ (*arguments, **keywords)
        self.dropTarget = _DropTarget(self)
        # If it is a grid, then we need to use grid window rather than self
        try:
            window = self.GetGridWindow()
        except AttributeError:
            window = self
        window.SetDropTarget(self.dropTarget)
        
    def OnRequestDrop(self, x, y):
        """
        Override this to decide whether or not to accept a dropped 
        item.
        """
        result = DraggedFromWidget is not self
        if DraggedFromWidget is not None:
            DraggedFromWidget.dropResult = result # part of workaround for bug 4128
        return result
        
    def OnEnter(self, x, y, dragResult):
        """
        Override this to perform an action when a drag enters your widget.
        
        @return a wxDragResult other than dragResult if you want to change the drag operation
        """
        # default - don't allow dragging to ourself
        if DraggedFromWidget is self:
            return wx.DragNone
        return dragResult

    def OnHover(self, x, y, dragResult):
        """
        Override this to perform an action when a drag cursor is
        hovering over the widget.
        
        @return a wxDragResult other than dragResult if you want to change the drag operation
        """
        # default - don't allow dragging to ourself
        if DraggedFromWidget is self:
            return wx.DragNone
        return dragResult

    def OnLeave(self):
        """
        Override this to perform an action when hovering terminates.
        """
        pass

    def SetCustomCursor(self, dragResult, cursorFilename):
        self.SetCursor(self._DROP_ICON(cursorFilename))
        DraggedFromWidget.dropSource.OverrideFeedback(dragResult)

    def _DROP_ICON(self, filename):
        # This macro from wxWidgets is going to be in wxPython soon.
        img = wx.GetApp().GetRawImage(filename)
        if img is None:
            return None
        return wx.CursorFromImage(img)


class DropSourceWithFeedback(wx.DropSource):
    """
    DropSource that can give custom cursor feedback.
    """
    def __init__(self, *args, **keys):
        super(DropSourceWithFeedback, self).__init__(*args, **keys)
        self.customFeedback = wx.DragError

    def OverrideFeedback(self, dragResult):
        """
        Set the one-shot dragResult to override feedback for.
        """
        self.customFeedback = dragResult # temporarily override copy feedback

    def GiveFeedback(self, effect):
        """
        Callback from inside wx DropSource::DoDragDrop()
        """
        override = self.customFeedback
        self.customFeedback = wx.DragError # back to normal feedback next time
        return effect is override


class _DropTarget(wx.DropTarget):
    """
    An instance of this class is a helper object that associates
    a wx.DropTarget with a receiver - a DropReceiveWidget.
    """
    def __init__(self, receiver):
        super (_DropTarget, self).__init__ ()
        self.receiver = receiver
        # create a data object for the kind of data we'll accept
        self.dataObject = receiver.ClipboardDataObject()
        self.SetDataObject(self.dataObject)
    
    def OnDrop(self, x, y):
        return self.receiver.OnRequestDrop(x, y)
    
    def OnData(self, x, y, dragResult):
        if self.GetData():
            dataToPaste = self.dataObject
            self.receiver.PasteData(dataToPaste)
        return dragResult
    
    def OnDragOver(self, x, y, dragResult):
        # map "move" to "copy" if copyOnly set
        if    (dragResult == wx.DragMove 
               and DraggedFromWidget is not None 
               and DraggedFromWidget.copyOnly):
            dragResult = wx.DragCopy
        return self.receiver.OnHover(x, y, dragResult)
        
    def OnEnter(self, x, y, dragResult):
        # map "move" to "copy" if copyOnly set
        if    (dragResult == wx.DragMove 
               and DraggedFromWidget is not None 
               and DraggedFromWidget.copyOnly):
            dragResult = wx.DragCopy
        return self.receiver.OnEnter(x, y, dragResult)

    def OnLeave(self):
        self.receiver.OnLeave()

class _ClipboardHandler(object):
    if __debug__:
        def __init__(self, *args, **keys):
            super(_ClipboardHandler, self).__init__(*args, **keys)
            self.clipboardHandlerInited = True

    def ClipboardDataFormat(self):
        raise NotImplementedError

    def DataObjectFormat(self):
        format = self.ClipboardDataFormat()
        if isinstance(format, int):
            return wx.DataFormat(format)
        else:
            return wx.CustomDataFormat(format)

    def GetDragData(self):        
        """
        Return the data being dragged onto self
        """
        if DraggedFromWidget is None:
            return None
        dataObject = DraggedFromWidget.dataObject
        # ask the dragged from widget to convert the data to our format, if possible.
        return DraggedFromWidget.NativeData(dataObject, self.DataObjectFormat())

class TextClipboardHandler(_ClipboardHandler):
    """
    Mixin class to give your widget Text-based clipboard handling.
    """
    def CopyData(self):
        """
        Called to get a widget's data at the beginning of a Copy or DnD.
        Returns a wxDataObject variant for use in Drag and Drop, or Cut and Paste.
        This implementation returns a Text data object.
        """
        dataObject = wx.TextDataObject()
        dataObject.SetText(self.GetStringSelection())
        return dataObject

    def PasteData(self, data):
        """
        Paste the supplied data into ourself, either
        because of a Paste operation, or a Drag and Drop.
        Assumes that the datum is Text.
        """
        text = data.GetText()
        self.WriteText(text)

    def ClipboardDataFormat(self):
        """
        Override to define which kinds you allow to be dropped.
        """
        return wx.DF_TEXT # Default is any kind of Text.

    def ClipboardDataObject(self):
        return wx.TextDataObject()
    
    def NativeData(self, rawObject, dataFormat):
        # convert the raw data into native data of the desired format
        if dataFormat != self.ClipboardDataFormat():
            return None
        return rawObject.GetText()

    """ 
    EditText widgets already implement CanCopy, CanCut, CanPaste,
    Copy, Cut, Paste, etc, so we don't need to here.
    """

class ItemClipboardHandler(_ClipboardHandler):
    """
    Mixin class to give your widget Item-based clipboard handling.
    Defines methods to Cut & Paste, and enable the menus.
    Calls back to your widget for Item-based selection handling:
        SelectedItems(), DeleteSelection(), AddItems(), etc
    """
    def AddItems(self, itemList):
        """
        Override this to add the dropped items to your widget.
        """
        pass
    
    def SelectedItems(self):
        """
        Override this to return the list of selected items.
        """
        return []
    
    def DeleteSelection(self):
        """
          Override this to remove the selection.
        """
        pass
    
    def CopyData(self):
        """
        Called to get a widget's data at the beginning of a Copy or DnD.
        Returns a wxDataObject variant for use in Drag and Drop, or Cut and Paste.
        This implementation deals with Items using UUIDs, using the Content Model
            to determine what formats to export.
        """
        compositeObject = wx.DataObjectComposite()

        # Build a dictonary of Item data formats
        self.exportDict = {}
        items = self.SelectedItems()
        for item in items:
            # add to the 'Item' list of our dictionary
            self.ExportItemFormat(item, 'Item')
            try:
                # ask the ContentItem to append its kinds too
                item.ExportItemData(self)
            except AttributeError:
                pass

        # now create a custom data object for each kind
        for format, itemList in self.exportDict.items():
            customData = wx.CustomDataObject(wx.CustomDataFormat(format))
            customData.SetData(self.ExportClipboardItems(itemList))
            compositeObject.Add(customData)

        return compositeObject

    def ExportItemFormat(self, item, format):
        # Callback for the ContentModel to tell us what format data to export.
        # Builds a dictionary keyed by format with a lists of item UUID strings.
        itemList = self.exportDict.setdefault(format, [])
        itemList.append(item)

    def ExportClipboardItems(self, items):
        return ','.join([str(item.itsUUID) for item in items])

    def ImportClipboardItems(self, rawData):
        itemList = []
        for itemUUID in rawData.split(','):
            item = self.blockItem.findUUID(itemUUID)
            if item is not None:
                itemList.append(item)
        return itemList

    def ClipboardDataFormat(self):
        """
        Override to define which kind you allow to be dropped.
        """
        return "Note" # Default is any kind of Note or subclass of Note.
    
    def ClipboardDataObject(self):
        format = self.ClipboardDataFormat()
        return wx.CustomDataObject(wx.CustomDataFormat(format))

    def CanCopy(self):
        try:
            items = self.SelectedItems()
        except AttributeError:
            return False
        return len(items) > 0

    def CanCut(self):
        if not hasattr (self, 'DeleteSelection'):
            return False
        return self.CanCopy()

    def Copy(self):
        items = []
        clipboard = wx.TheClipboard
        if clipboard.Open():
            items = self.SelectedItems()
            data = self.CopyData()
            clipboard.SetData(data)
            clipboard.Close()
        return items

    def Cut(self):
        result = self.Copy()
        try:
            self.DeleteSelection()
        except AttributeError:
            pass # doesn't know DeleteSelection()
        return result

    def CanPaste(self):
        clipboard = wx.TheClipboard
        formatWeCanPaste = self.DataObjectFormat()
        supportsOurKinds = clipboard.IsSupported(formatWeCanPaste)
        return supportsOurKinds

    def Paste(self):
        clipboard = wx.TheClipboard
        if clipboard.Open():
            dataToPaste = self.ClipboardDataObject()
            if clipboard.GetData(dataToPaste):
                self.PasteData(dataToPaste)
            clipboard.Close()

    def PasteData(self, data):
        """
        Paste the supplied data into ourself, either
        because of a Paste operation, or a Drag and Drop.
        Assumes that the data are Items, override for other kinds.
        """
        rawData = data.GetData()
        itemList = self.ImportClipboardItems(rawData)
        if len(itemList)>0:
            self.AddItems(itemList)

    def NativeData(self, rawObject, dataFormat):
        # convert the raw data into native data of the desired format
        rawData = rawObject.GetDataHere(dataFormat)
        return self.ImportClipboardItems(rawData)

