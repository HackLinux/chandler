from SideBar import SidebarBlock
from SideBar import CPIATestSidebarBPBDelegate, SidebarBPBDelegate


def installParcel(parcel, oldVersion=None):
    from mainblocks import make_mainview
    from summaryblocks import make_summaryblocks
    make_mainview(parcel)
    make_summaryblocks(parcel)
    
    from osaf.framework import prompts

    prompts.DialogPref.update(parcel, "clearCollectionPref")
    
                              
