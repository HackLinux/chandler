from Styles import CharacterStyle, ColorStyle, Style
from Block import Block as __Block
from application import schema
import wx


from Block import (
    RectangularChild, BlockEvent, NewItemEvent, ChoiceEvent, ColorEvent,
    KindParameterizedEvent, AddToSidebarEvent, NewBlockWindowEvent, 
    EventList, debugName, getProxiedItem, WithoutSynchronizeWidget,
    IgnoreSynchronizeWidget
)

from ContainerBlocks import (
    BoxContainer, FrameWindow, LayoutChooser, ScrolledContainer,
    SplitterWindow, TabbedContainer, ViewContainer
)

from BranchPoint import BranchPointDelegate, BranchPointBlock, BranchSubtree

from Views import View

from ControlBlocks import (
    AEBlock, Button, ContentItemDetail,
    ContextMenu, ContextMenuItem, EditText, HTML, ItemDetail,
    ReminderTimer, StaticText, StatusBar, Timer, Tree, PresentationStyle, Column
)

from Table import (
    Table, wxTable, GridCellAttributeEditor
)

from MenusAndToolbars import (
    DynamicBlock, DynamicChild, DynamicContainer, Menu, MenuBar, MenuItem,
    RefCollectionDictionary, Toolbar, ToolbarItem
)

from ColumnHeaderBlocks import (ColumnHeader) 

from PimBlocks import (FocusEventHandlers)

def installParcel(parcel, oldName=None):

    # Block Events instances.  Applicaiton specific events should not
    # be located here.  Instead put them in a View in your
    # application. Also don't put any references to application
    # specific parcels here.

    EventList.update(parcel, 'GlobalEvents',
        eventsForNamedLookup=[
            BlockEvent.template('Undo',
                                dispatchEnum = 'FocusBubbleUp').install(parcel),
            
            BlockEvent.template('Cut',
                                dispatchEnum = 'FocusBubbleUp',
                                commitAfterDispatch = True).install(parcel),
    
            BlockEvent.template('SelectAll',
                                dispatchEnum = 'ActiveViewBubbleUp').install(parcel),
    
            BlockEvent.template('PrintPreview').install(parcel),
    
            BlockEvent.template('Remove',
                                dispatchEnum = 'FocusBubbleUp',
                                commitAfterDispatch = True).install(parcel),
    
            BlockEvent.template('Clear',
                                dispatchEnum = 'FocusBubbleUp',
                                commitAfterDispatch = True).install(parcel),
    
            BlockEvent.template('Paste',
                                dispatchEnum = 'FocusBubbleUp',
                                commitAfterDispatch = True).install(parcel),

            BlockEvent.template('Print',
                                dispatchEnum = 'ActiveViewBubbleUp').install(parcel),
    
            BlockEvent.template('Copy',
                                dispatchEnum = 'FocusBubbleUp',
                                commitAfterDispatch = True).install(parcel),
    
            BlockEvent.template('Redo',
                                dispatchEnum = 'FocusBubbleUp').install(parcel),
    
            BlockEvent.template('Quit',
                                dispatchEnum = 'ActiveViewBubbleUp').install(parcel),
    
            BlockEvent.template('About',
                                dispatchEnum = 'ActiveViewBubbleUp').install(parcel),
    
            BlockEvent.template('Close',
                                dispatchEnum = 'ActiveViewBubbleUp').install(parcel),
    
            BlockEvent.template('Open',
                                dispatchEnum = 'ActiveViewBubbleUp').install(parcel),
    
            BlockEvent.template('SelectItemsBroadcast',
                                dispatchEnum = 'BroadcastInsideMyEventBoundary',
                                methodName='onSelectItemsEvent').install(parcel),
            
            BlockEvent.template('SetContents',
                                dispatchEnum = 'BroadcastInsideMyEventBoundary').install(parcel),
            
            BlockEvent.template('Rename',
                                dispatchEnum = 'FocusBubbleUp').install(parcel),
    
            BlockEvent.template('EnterPressed',
                                dispatchEnum = 'BroadcastInsideMyEventBoundary').install(parcel),
        ])

    BlockEvent.template(
        'SelectedItemChanged',
        dispatchEnum = 'BroadcastEverywhere').install(parcel)    

    # A few specific styles

    CharacterStyle.update(parcel, "TextStyle", fontFamily="DefaultUIFont")

    CharacterStyle.update(parcel, "BigTextStyle",
        fontFamily="DefaultUIFont", fontSize = 15, fontStyle = "bold",
    )
    CharacterStyle.update(parcel, "LabelStyle", fontFamily="DefaultUIFont")

    CharacterStyle.update(parcel, "SummaryHeaderStyle",
        fontFamily="DefaultUIFont", fontStyle = "bold",
    )

    CharacterStyle.update(parcel, "SummaryRowStyle", fontFamily="DefaultUIFont")

    CharacterStyle.update(parcel, "SidebarRowStyle", fontFamily="DefaultUIFont", fontSize=12)
