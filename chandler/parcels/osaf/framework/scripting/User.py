import wx
from application import schema, Globals

"""
Emulating User-level Actions
"""
def emulate_typing(string, ctrlFlag = False, altFlag = False, shiftFlag = False):
    """ emulate_typing the string into the current focused widget """
    success = True
    def set_event_info(event):
        # setup event info for a keypress event
        event.m_keyCode = keyCode
        event.m_rawCode = keyCode
        event.m_shiftDown = char.isupper() or shiftFlag
        event.m_controlDown = event.m_metaDown = ctrlFlag
        event.m_altDown = altFlag
        event.SetEventObject(widget)
    # for each key, check for specials, then try several approaches
    app = wx.GetApp()
    for char in string:
        keyCode = ord(char)
        if keyCode == wx.WXK_RETURN:
            emulate_return()
        elif keyCode == wx.WXK_TAB:
            emulate_tab(shiftFlag=shiftFlag)
        else:
            # in case the focus has changed, get the new focused widget
            widget = wx.Window_FindFocus()
            if widget is None:
                success = False
            else:
                # try calling any bound key handler
                keyPress = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
                set_event_info(keyPress)
                downWorked = widget.ProcessEvent(keyPress)
                keyUp = wx.KeyEvent(wx.wxEVT_KEY_UP)
                set_event_info(keyUp)
                upWorked = widget.ProcessEvent(keyUp)
                if not (downWorked or upWorked): # key handler worked?
                    # try calling EmulateKeyPress

                    emulateMethod = getattr(widget, 'EmulateKeyPress',
                                            lambda k: False)

                    if ('__WXMSW__' in wx.PlatformInfo or
                        not emulateMethod(keyPress)): # emulate worked?
                        # try calling WriteText
                        writeMethod = getattr(widget, 'WriteText', None)
                        if writeMethod:
                            writeMethod(char)
                        else:
                            success = False # remember we had a failure
                if success:
                    app.Yield()
    return success

def emulate_tab(shiftFlag=False):
    if shiftFlag:
        flags = wx.NavigationKeyEvent.IsBackward
    else:
        flags = wx.NavigationKeyEvent.IsForward
    wx.Window_FindFocus().Navigate(flags)

def emulate_click(block, x=None, y=None, double=False, **kwds):
    """
    Simulates left mouse click on the given block or widget.
    
    You can pass in special keyword parameters like control=True to
    emulate that certain buttons are down. Supported values are
    control, shift, meta, and alt
    """
    try:
        widget =  block.widget
    except AttributeError:
        widget = block
    # grids have an inner window that recieves the events. Note that
    # this does NOT allow you to click on the column header. For that
    # use widget.GetGridColLabelWindow()
    if isinstance(widget, wx.grid.Grid):
        widget = widget.GetGridWindow()
        
    # Checkboxes don't seem to toggle based on manufactured mouse clicks,
    # (bug 3336) so we fake it.
    if isinstance(widget, wx.Button):
        clickEvent = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED)
        clickEvent.SetEventObject(widget)
        widget.ProcessEvent(clickEvent)
    elif isinstance(widget, wx.CheckBox):
        widget.SetValue(not widget.GetValue())
        clickEvent = wx.CommandEvent(wx.wxEVT_COMMAND_CHECKBOX_CLICKED)
        clickEvent.SetEventObject(widget)
        widget.ProcessEvent(clickEvent)
    else: # do it the normal way   
        # event settings
        mouseEnter = wx.MouseEvent(wx.wxEVT_ENTER_WINDOW)
        if double:
            mouseDown = wx.MouseEvent(wx.wxEVT_LEFT_DCLICK)
        else:
            mouseDown = wx.MouseEvent(wx.wxEVT_LEFT_DOWN)
        mouseUp = wx.MouseEvent(wx.wxEVT_LEFT_UP)
        mouseLeave = wx.MouseEvent(wx.wxEVT_LEAVE_WINDOW)
        if x:
            mouseEnter.m_x = mouseDown.m_x = mouseUp.m_x = x
        if y:
            mouseEnter.m_y = mouseDown.m_y = mouseUp.m_y = y
    
        for event in (mouseEnter, mouseDown, mouseUp, mouseLeave):
            event.SetEventObject(widget)
            for keyDown in 'control', 'alt', 'shift', 'meta':
                if kwds.get(keyDown):
                    setattr(event, 'm_' + keyDown + 'Down', kwds.get(keyDown))
    
        # events processing
        widget.ProcessEvent(mouseEnter)
        widget.ProcessEvent(mouseDown)
        if not double:
            widget.ProcessEvent(mouseUp)
        widget.ProcessEvent(mouseLeave)
    # Give Yield to the App
    wx.GetApp().Yield()

def emulate_return(block=None):
    """ Simulates a return-key event in the given block """
    try:
        if block :
            widget = block.widget
        else :
            widget = wx.Window_FindFocus()
    except AttributeError:
        return False
    else:
        # return-key down
        ret_d = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
        ret_d.m_keyCode = wx.WXK_RETURN
        ret_d.SetEventObject(widget)
        # return-key up
        ret_up = wx.KeyEvent(wx.wxEVT_KEY_UP)
        ret_up.m_keyCode = wx.WXK_RETURN
        ret_up.SetEventObject(widget)
        # text updated event
        tu = wx.CommandEvent(wx.wxEVT_COMMAND_TEXT_UPDATED)
        tu.SetEventObject(widget)
        # kill focus event
        kf = wx.FocusEvent(wx.wxEVT_KILL_FOCUS)
        kf.SetEventObject(widget)
        # Text enter
        ent = wx.CommandEvent(wx.wxEVT_COMMAND_TEXT_ENTER)
        ent.SetEventObject(widget)

        #work around for mac bug
        widget.ProcessEvent(tu) #for start/end time and location field
        #work around for canvasItem
        widget.ProcessEvent(kf) #for canvasItem title
        # events processing
        widget.ProcessEvent(ret_d)
        widget.ProcessEvent(ret_up)
        # Give Yield & Idle to the App
        idle()
        return True

def emulate_sidebarClick(sidebar, cellName, double=False, overlay=False):
    ''' Process a left click on the given cell in the given sidebar
        if overlay is true the overlay disk next to the collection name is checked
        otherwise the collection is selected'''
    #determine x coordinate offset based on overlay value
    xOffset = 24
    if overlay:
        xOffset=3 

    # find special collections by item because their names may
    # change (i.e. "All" becomes "My Items" or "My Calendar
    # Events" etc...
    pim_ns = schema.ns('osaf.pim', Globals.mainViewRoot)
    chandler_collections = {"All":pim_ns.allCollection}
    if cellName in chandler_collections.keys():
        cellName = chandler_collections[cellName]

    cellRect = None
    for i in range(sidebar.widget.GetNumberRows()):
        item = sidebar.widget.GetTable().GetValue(i,0)[0]
        if item.displayName == cellName or item is cellName:
            cellRect = sidebar.widget.CalculateCellRect(i)
            break
    if cellRect:
        # events processing
        gw = sidebar.widget.GetGridWindow()
        # +3 work around for the sidebar bug
        emulate_click(gw, x=cellRect.GetX()+xOffset, y=cellRect.GetY()+3, double=double)
        return True
    else:
        return False

def idle():
    app = wx.GetApp()
    app.Yield()
    app.ProcessEvent(wx.IdleEvent())
    app.Yield()
