__version__ = "$Revision$"
__date__ = "$Date$"
__copyright__ = "Copyright (c) 2004 Open Source Applications Foundation"
__license__ = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

import application.Globals as Globals
import Block as Block
import logging
import wx

class RefCollectionDictionary(object):
    """
      Provides dictionary access to a reference collection attribute 
    L{RefDict<repository.item.ItemRef.RefDict>}.
    The attribute that contains the reference collection is determined
    through attribute indirection using the collectionSpecifier attribute.
    The "itsName" property of the items in the reference collection
    is used for the dictionary lookup by default.  You can override
    the name accessor if you want to use something other than
    itsName to key the items in the collection.
    """
    def __init__(self):
        # ensure that the collectionSpecifier exists
        if not self.hasAttributeValue(self.collectionSpecifier()):
            self.setAttributeValue(self.collectionSpecifier(), [])
        
    def itemNameAccessor(self, item):
        """
        Name accessor used for RefCollectionDictionary
        subclasses can override this method if they want to
        use something other than the itsName property to 
        determine item names.
        
        @param item: the item whose name we want.
        @type item: C{item}
        @return: a C{immutable} for the key into the collection
        """
        return item.itsName
    
    def collectionSpecifier(self):
        """
        determines which attribute to use for the
        collectionSpecifier.
        subclasses can override this method if they want to
        use something other than collectionSpecifier, 
        which is typlically set up to redirect to the actual
        attribute that contains the collection.
        @return: a C{String} for the name of the collection attribute
        """
        return 'collectionSpecifier' # should be a redirectTo attribute

    def _index(self, key):
        """
        returns a tuple with the item refered to by the key, and the collection
        @param key: the key used for lookup into the ref collection.
        @type key: C{immutable}, typically C{String}
        @return: a C{Tuple} containing C{(item, collection)} or raises an exception if not found.
        """
        coll = self.getAttributeValue(self.collectionSpecifier())
        return (coll.getByAlias(key), coll)
        
    def index(self, key):
        """
        returns the item refered to by the key
        @param key: the key used for lookup into the ref collection.
        @type key: C{immutable}, typically C{String}
        @return: C{item} if found, or C{None} if not found.
        """
        try:
            i, coll = self._index(key)
            return i
        except KeyError:
            return None
        
    def __iter__(self):
        """
        Returns an iterator to the collection attribute.
        """
        return iter(self.getAttributeValue(self.collectionSpecifier()))
 
    def __len__(self):
        """
        @return: C{int} length of the collection attribute.
        """
        # In case our collection doesn't exist return zero
        try:
            return len(self.getAttributeValue(self.collectionSpecifier()))
        except AttributeError:
            return 0
    
    def has_key(self, key):
        """
        @param key: the key used for lookup into the ref collection.
        @type key: C{immutable}, typically C{String}
        @return: C{True} if found, or {False} if not found.
        """
        return self.index(key) != None
                                      
    def __contains__(self, item):
        """
        @param item: an item to find in the ref collection.
        @type key: C{item}
        @return: C{True} if found, or {False} if not found.
        """
        coll = self.getAttributeValue(self.collectionSpecifier())
        return coll.get(item.itsUUID) != None
    
    def __getitem__(self, key):
        """
        return the item associated with the key from the ref collection attribute
        @param key: the key used for lookup into the ref collection.
        @type key: C{immutable}, typically C{String}
        @return: C{item} if found, or raises an exception.
        """
        return self._index(key)[0]
    
    def __setitem__(self, key, value):
        """
        replace the item associated with the key from the ref collection attribute.
        Note that the new item may have a different key, but it will be placed
        in the same position in the ref collection, and the keyed item will be removed.
        @param key: the key used for position lookup into the ref collection.
        @type key: C{immutable}, typically C{String}
        @param value: the C{item} to place into the ref collection.
        @type value: C{item}
        """
        itemIndex, coll = self._index(key) # find the keyed item
        self.insert(itemIndex, value) # insert before
        coll.removeItem(itemIndex) # remove keyed original
            
    def insert(self, index, item):
        """
        Insert item before index in our ref collection.
        @param index: the position used for insertion into the ref collection.
        @type index: C{item} that exists in the ref collection, or C{None} to append.
        @param item: the C{item} to insert before C{index} in the ref collection.
        @type item: C{item}
        """
        # 
        coll = self.getAttributeValue(self.collectionSpecifier())
        coll.append(item, alias=self.itemNameAccessor(item))
        if index is not None:
            prevItem = coll.previous(index)
            coll.placeItem(item, prevItem) # place after the previous item
            
    def __delitem__(self, key):
        """
        Delete the keyed item from our ref collection.
        @param key: the key used for item location in the ref collection.
            Throws an exception if there is no item associated with the key.
        @type key: C{immutable}, typically C{String}
        """
        itemIndex, coll = self._index(key)
        coll.removeItem(itemIndex)

class DynamicChild (object):
    # Abstract mixin class used to detect DynamicChild blocks
    pass

class DynamicContainer(RefCollectionDictionary):
    """
      A block whose children are built dynamically, when the
    Active View changes.
    This list of children is in "dynamicChildren" and the
    back pointer is in "dynamicParent".
    """                
    def itemNameAccessor(self, item):
        """
          Use blockName for the accessor
        """
        return item.blockName
    
    def rebuildDynamicContainers(cls, startingAtBlock, dynamicChildBlock):
        """
           rebuildDynamicContainers rebuilds the dynamic
        container hierarchy based on the blocks it finds in
        a root section of the static block hierarchy.  Dynamic
        associations between blocks are done by itemName, 
        which must be unique.  Upon exit all DynamicContainer
        blocks found will have references to all dynamicChildren
        found, and those blocks will have an inverse reference
        to their dynamicParent.

          The rebuild is done starting at the specified block,
        first scanning all of its childrenBlocks, and then
        moving up to the parentBlock, repeating this process
        until reaching the root of the hierarchy.
        
          DynamicContainers and their dynamicChildren are 
        identified by their itemName rather than their UUIDs,
        to make it easy for third party parcels to add menus. 
        This requires all container names to be unique
        and all names of dynamicChildren to be unique within
        their container.  

        @param startingAtBlock: the starting block for the scan.
        @type startingAtBlock: C{Block}
        @param dynamicChildBlock: a L{DynamicChild}, used to determine if
                if we have every rebuilt the dynamic container hierarchy.
        @type dynamicChildBlock: C{DynamicChild}
        """
        
        def rebuildContainers(block, containers):
            """
              scan one level of the static hierarchy looking for dynamic containers.
            """
            parent = block.parentBlock
            if (parent):
                rebuildContainers (parent, containers)
            for child in block.childrenBlocks:
                # pick up container definitions
                if isinstance (child, DynamicContainer):
                    child.dynamicChildren = [] # rebuild children from scratch
                    containers [child.blockName] = child
                                           
        def rebuildChildren(block, containers):
            """
              scan one level of the static hierarchy looking for dynamic children.
            """
            parent = block.parentBlock
            if (parent):
                rebuildChildren (parent, containers)
            for child in block.childrenBlocks:
                # pick up children
                if isinstance (child, DynamicChild):
                    """
                      Use location to look up the container that
                    contains the entry or container
                    
                      If you get an exception here, it's probably because
                    the name of the location isn't the name of an existing
                    bar (bar needs to be listed before items).
                        """
                    locationName = child.location
                    if not locationName:
                        locationName = 'MenuBar'
                    bar = containers [locationName]
                    
                    if child.operation == 'InsertBefore':
                        # Shouldn't have items with the same name, unless they are the same
                        if __debug__:
                            if not child in bar:
                                if bar.has_key(child.blockName):
                                    logging.warning("%s already has a %s named %s" % (bar.blockName, child.blockName, child.blockName))
                        i = bar.index(child.itemLocation)
                        bar.insert(i, child)
                    elif child.operation == 'Replace':
                        bar[child.itemLocation] = child
                    elif child.operation == 'Delete':
                        """
                          If you get an exception here, it's probably because
                        you're trying to remove a bar item that doesn't exist.
                        """
                        del bar[child.itemLocation]
                    else:
                       assert (False)
        """
          Should we rebuild the dynamic container hierarchy?
        Not needed if we already have a persisted hierarchy
        and we're currently ignoring synchronize widget.
        """
        if dynamicChildBlock.hasAttributeValue("dynamicParent") and \
           Globals.wxApplication.ignoreSynchronizeWidget:
            return
        
        """
          Rebuild the dynamic container hierarchy.
        First establish all containers, then insert their children
        so the block declarations can be order-independent.
        """
        containers = {}
        rebuildContainers(startingAtBlock, containers)
        rebuildChildren(startingAtBlock, containers)
        """
          Now that the we have the new dynamic structure, 
        update the blocks that have changed and call synchronizeWidget on them
        so they know to redraw.
        """
        # Help users who forget to put a location attribute on a menuItem or toolbarItem
        for menu in containers['MenuBar']:
            assert isinstance(menu, Menu), "Non-Menu block named %s found in \
                 Menu Bar (specify a location attribute)" % menu.blockName 
        for bar in containers.values():
            bar.synchronizeWidget()
    rebuildDynamicContainers=classmethod(rebuildDynamicContainers)

class wxMenuItem (wx.MenuItem):
    def __init__(self, style, *arguments, **keywords):
        # unpack the style arguments, wx expects them separately
        arguments = style + arguments
        super (wxMenuItem, self).__init__ (*arguments, **keywords)

    def wxSynchronizeWidget(self):
        # placeholder in case Menu Items change
        pass
    
    def CalculateWXStyle(cls, block):
        parentWidget = block.dynamicParent.widget
        if block.menuItemKind == "Separator":
            id = wx.ID_SEPARATOR
            kind = wx.ITEM_SEPARATOR
            style = (parentWidget, id, "", "", kind, None)
        else:
            """
              Menu items must have an event, otherwise they can't cause any action,
            nor can we use wxWindows api's to distinguish them from each other.
            """
            assert block.hasAttributeValue('event')
            id = Block.Block.getWidgetID(block)
            if block.menuItemKind == "Normal":
                kind = wx.ITEM_NORMAL
            elif block.menuItemKind == "Check":
                kind = wx.ITEM_CHECK
            elif block.menuItemKind == "Radio":
                kind = wx.ITEM_RADIO
            else:
                assert (False)        
            title = block.title
            if len(block.accel) > 0:
                title = title + "\tCtrl+" + block.accel
            
            """
              When inserting ourself into a MenuItem, we must actually
            insert ourself into the submenu of that MenuItem.
            """
            if isinstance (parentWidget, wxMenu):
                style = (parentWidget, id, title, block.helpString, kind, None)
            else:
                assert isinstance (parentWidget, wxMenuItem)
                submenu = block.GetSubMenu()
                assert submenu
                style = (None, id, title, block.helpString, kind, submenu)
        return style
    CalculateWXStyle = classmethod(CalculateWXStyle)
    
    def setMenuItem (self, newItem, oldItem, index):
        subMenu = self.GetSubMenu()
        assert isinstance (subMenu, wxMenu)
        subMenu.setMenuItem(newItem, oldItem, index)
        
    def getMenuItems(self):
        wxMenuObject = self.GetSubMenu()
        assert isinstance (wxMenuObject, wxMenu)
        return wxMenuObject.GetMenuItems()

class wxMenu(wx.Menu):
    def __init__(self, *arguments, **keywords):
        super (wxMenu, self).__init__ (*arguments, **keywords)

    def wxSynchronizeWidget(self):
        self.blockItem.synchronizeItems()
    """
      wxWindows doesn't implement convenient menthods for dealing
    with menus, so we'll write our own: getMenuItems, deleteItem
    getItemTitle, and setMenuItem
    """
    def getMenuItems (self):
        return self.GetMenuItems()
    
    def getItemTitle (self, index, item):
        id = item.GetId()
        title = self.GetLabel (id)
        return title
    
    def deleteItem (self, index, oldItem):
        self.DestroyItem (oldItem)
            
    def setMenuItem (self, newItem, oldItem, index):
        # now set the menu item
        itemsInMenu = self.GetMenuItemCount()
        assert (index <= itemsInMenu)
        if index < itemsInMenu:
            self.deleteItem (index, oldItem)
        if isinstance (newItem.widget, wxMenuItem):
            success = self.InsertItem (index, newItem.widget)
            assert success
        else:
            self.InsertMenu (index, 0, newItem.title, newItem.widget, newItem.helpString)
        
class wxMenuBar(wx.MenuBar):
    def __init__(self, *arguments, **keywords):
        super (wxMenuBar, self).__init__ (*arguments, **keywords)
        # install the menu bar in the main frame
        frame = Globals.wxApplication.mainFrame
        if frame:
            frame.SetMenuBar(self)

    def wxSynchronizeWidget(self):
        self.blockItem.synchronizeItems()
            
    """
      wxWindows doesn't implement convenient menthods for dealing
    with menus, so we'll write our own: getMenuItems, deleteItem
    getItemTitle, and setMenuItem
    """
    def getMenuItems (self):
        menuList = []
        for index in xrange (self.GetMenuCount()):
            menuList.append (self.GetMenu (index))
        return menuList
        
    def getItemTitle (self, index, item):
        title = wxMenuObject.GetLabelTop (index)
        return title
    
    def deleteItem (self, index, oldItem):
        oldMenu = self.Remove (index)
        oldMenu.Destroy()
        
    def setMenuItem (self, newItem, oldItem, index):
        itemsInMenu = self.GetMenuCount()
        assert (index <= itemsInMenu)
        title = newItem.title
        if index < itemsInMenu:
            oldMenu = self.Replace (index, newItem.widget, title)
            assert oldMenu == oldItem
            oldMenu.Destroy()
        else:
            success = self.Append (newItem.widget, title)
            assert success

class MenuItem (Block.Block, DynamicChild):
    def instantiateWidget (self):
        # We'll need a dynamicParent's widget in order to instantiate
        try:
            if isinstance(self.dynamicParent.widget, wxMenu):
                return wxMenuItem(style=wxMenuItem.CalculateWXStyle(self))
        except AttributeError:
            return None
        
class MenuBar(Block.Block, DynamicContainer):
    def instantiateWidget (self):
        return wxMenuBar()

    def synchronizeItems(self):
        """
          Install the menus into supplied menu list, and submenus
        into their menu items.
        """
        oldMenuList = self.widget.getMenuItems ()
        
        index = 0
        for menuItem in self.dynamicChildren:
            # ensure that the menuItem has been instantiated
            if not menuItem.hasAttributeValue("widget"):
                menuItem.widget = menuItem.instantiateWidget()
                menuItem.widget.blockItem = menuItem
            menuItem.widget.wxSynchronizeWidget()

            try:
                oldItem = oldMenuList.pop(0)
            except IndexError:
                oldItem = None

            if not menuItem is oldItem:
                # set the new item in the menu
                self.widget.setMenuItem (menuItem, oldItem, index)

            index += 1
                
        for oldItem in oldMenuList:
            self.widget.deleteItem (index, oldItem)
            index += 1

class Menu(MenuBar, DynamicChild):
    def instantiateWidget (self):
        return wxMenu()
    
"""  
Toolbar classes
"""

class wxToolbar(wx.ToolBar):
    def __init__(self, *arguments, **keywords):
        super (wxToolbar, self).__init__ (*arguments, **keywords)
        self.toolItemList = []
        self.toolItems = 0
        
    def wxSynchronizeWidget(self):
        self.SetToolBitmapSize((self.blockItem.toolSize.width, self.blockItem.toolSize.height))
        self.SetToolSeparation(self.blockItem.separatorWidth)
        self.blockItem.synchronizeColor()
        
        # check if anything has changed in this toolbar
        rebuild = False
        if len(self.blockItem.dynamicChildren) != len(self.toolItemList):
            rebuild = True
        else:
            i = 0
            for item in self.blockItem.dynamicChildren:
                if item is not self.toolItemList[i]:
                    rebuild = True
                    break
                i += 1
        
        if rebuild:
            # For now, we just blow away the old toolbar, and build a new one
            for i in xrange(self.toolItems):
                self.DeleteToolByPos(0)
            self.toolItemList = []
            self.toolItems = 0
            
            # we should have a toolbar set up for us in the barList
            for item in self.blockItem.dynamicChildren:
                self.toolItems += item.addTool(self)
                self.toolItemList.append(item)
            self.Realize()
            # now disable any disabled items
            for item in self.blockItem.dynamicChildren:
                self.EnableTool(item.toolID, not item.disabled)
            
class Toolbar(Block.RectangularChild, DynamicContainer):
    def instantiateWidget (self):
        return wxToolbar(self.parentBlock.widget, 
                         Block.Block.getWidgetID(self),
                         wx.DefaultPosition,
                         (300, self.toolSize.height+2),
                         style=self.calculate_wxStyle())

    def calculate_wxStyle (self):
        style = wx.TB_HORIZONTAL
        if self.buttons3D:
            style |= wx.TB_3DBUTTONS
        else:
            style |= wx.TB_FLAT
        if self.buttonsLabeled:
            style |= wx.TB_TEXT
        return style
    
    def synchronizeColor (self):
        # if there's a color style defined, syncronize the color
        if self.hasAttributeValue("colorStyle"):
            self.colorStyle.synchronizeColor(self)
        
class ToolbarItem(Block.Block, DynamicChild):
    """
      Under construction
    """
    def addTool(self, wxToolbar):
        numItems = 1
        tool = None
        id = Block.Block.getWidgetID(self)
        self.toolID = id
        if self.toolbarItemKind == 'Button':
            bitmap = wx.Image (self.bitmap, 
                               wx.BITMAP_TYPE_PNG).ConvertToBitmap()
            if self.label:
                tool = wxToolbar.AddLabelTool (id, self.label, bitmap, 
                                               shortHelp=self.title, 
                                               longHelp=self.helpString)
            else:
                if self.toggle:
                    tool = wxToolbar.AddCheckTool (id, bitmap, 
                                                   shortHelp=self.title, 
                                                   longHelp=self.helpString)
                else:
                    tool = wxToolbar.AddSimpleTool (id, bitmap, 
                                                    self.title, self.helpString)
            # Bind events to the Application OnCommand dispatcher, which will
            #  call the block.event method
            wxToolbar.Bind (wx.EVT_TOOL, Globals.wxApplication.OnCommand, id=id)            
        elif self.toolbarItemKind == 'Separator':
            wxToolbar.AddSeparator()
            numItems = 1
        elif self.toolbarItemKind == 'Check':
            numItems = 0
        elif self.toolbarItemKind == 'Radio':
            bitmap = wx.Image (self.bitmap, 
                               wx.BITMAP_TYPE_PNG).ConvertToBitmap()
            if self.label:
                tool = wxToolbar.AddRadioLabelTool(id, self.label, bitmap,
                                                   shortHelp=self.title,
                                                   longHelp=self.helpString)
            else:
                tool = wxToolbar.AddRadioTool(id, bitmap, shortHelp=self.title,
                                              longHelp=self.helpString)
            # Bind events to the Application OnCommand dispatcher, which will
            #  call the block.event method
            wxToolbar.Bind (wx.EVT_TOOL, Globals.wxApplication.OnCommand, id=id)
        elif self.toolbarItemKind == 'Text':
            tool = wx.TextCtrl (wxToolbar, id, "", 
                               wx.DefaultPosition, 
                               wx.Size(300,-1), 
                               wx.TE_PROCESS_ENTER)
            tool.SetName(self.title)
            wxToolbar.AddControl (tool)
            tool.Bind(wx.EVT_TEXT_ENTER, Globals.wxApplication.OnCommand, id=id)
        elif self.toolbarItemKind == 'Combo':
            proto = self.prototype
            choices = proto.choices
            tool = wx.ComboBox (wxToolbar,
                            -1,
                            proto.selection, 
                            wx.DefaultPosition,
                            (proto.minimumSize.width, proto.minimumSize.height),
                            proto.choices)            
            wxToolbar.AddControl (tool)
            tool.Bind(wx.EVT_COMBOBOX, Globals.wxApplication.OnCommand, id=id)
            tool.Bind(wx.EVT_TEXT, Globals.wxApplication.OnCommand, id=id)
        elif self.toolbarItemKind == 'Choice':
            proto = self.prototype
            choices = proto.choices
            tool = wx.Choice (wxToolbar,
                            -1,
                            wx.DefaultPosition,
                            (proto.minimumSize.width, proto.minimumSize.height),
                            proto.choices)            
            wxToolbar.AddControl (tool)
            tool.Bind(wx.EVT_CHOICE, Globals.wxApplication.OnCommand, id=id)
        elif __debug__:
            assert False, "unknown toolbarItemKind"
            numItems = 0
        # splice in the tool as this item's widget
        # this isn't done automatically since ToolbarItems don't use
        # instantiateWidget
        # DLDTBD - figure out a way to have the block instantiate a widget
        # without having it show up anywhere until it gets added to the Toolbar.
        if tool is not None:
            self.widget = tool
            self.widget.blockItem = self
        return numItems

