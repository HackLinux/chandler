# -*- coding: utf-8 -*-
"""
Generate sample items: calendar, contacts, etc.
"""


__revision__  = "$Revision$"
__date__      = "$Date$"
__copyright__ = "Copyright (c) 2003-2004 Open Source Applications Foundation"
__license__ = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

import random

from datetime import datetime, timedelta
from PyICU import ICUtzinfo, UnicodeString
from osaf import pim
import osaf.pim.calendar.Calendar as Calendar
import osaf.pim.mail as Mail
import i18n

TEST_I18N = 'test' in i18n.getLocaleSet()
I18N_SEED = UnicodeString(u"йδ")

HEADLINES = [u"Dinner", u"Lunch", u"Meeting", u"Movie", u"Games"]

DURATIONS = [60, 90, 120, 150, 180]

REMINDERS = [None, None, None, None, 1, 10] # The "None"s make only a 30% chance an event will have a reminder...

def addSurrogatePairToText(text):
    #One in two chance. If the rand int return equals 1
    #then add a surrogate pair at the start and end of the text
    if random.randrange(2) == 1:
        start = random.randrange(I18N_SEED.length())
        end   = random.randrange(I18N_SEED.length())
        return  u"%s%s%s" % (I18N_SEED.charAt(start), text, I18N_SEED.charAt(end))
    return text


def GenerateCalendarParticipant(view):
    email = Mail.EmailAddress(view=view)
    domainName = random.choice(DOMAIN_LIST)
    handle = random.choice(LASTNAMES).lower()
    email.emailAddress = "%s@%s" % (handle, domainName)
    return email

IMPORTANCE = [u"important", u"normal", u"fyi"]
LOCATIONS  = [u"Home", u"Office", u"School"]



def GenerateCalendarEvent(view, days=30, tzinfo=None):
    event = Calendar.CalendarEvent(view=view)
    event.displayName = random.choice(HEADLINES)

    if TEST_I18N:
        event.displayName = addSurrogatePairToText(event.displayName)

    # Choose random days, hours
    startDelta = timedelta(days=random.randint(0, days),
                           hours=random.randint(0, 24))

    now = datetime.now(tzinfo)
    closeToNow = datetime(now.year, now.month, now.day, now.hour,
                          int(now.minute/30) * 30, tzinfo=now.tzinfo)
    event.startTime = closeToNow + startDelta

    # Events are anyTime by default. Give a 5% chance of allDay instead,
    # or 90% of a normal event.
    r = random.randint(0,100)
    if r < 95: # 5% chance that we'll leave anyTime on
        event.anyTime = False
    if r < 5: # 5% chance of allDay
        event.allDay = True

    # Choose random minutes
    event.duration = timedelta(minutes=random.choice(DURATIONS))
    
    # Maybe a nice reminder?
    reminderInterval = random.choice(REMINDERS)
    if reminderInterval is not None:
        event.reminderTime = event.startTime - timedelta(minutes=reminderInterval)
        
    # Add a location to 2/3 of the events
    if random.randrange(3) > 0:
        if TEST_I18N:
            event.location = Calendar.Location.getLocation(view, addSurrogatePairToText(random.choice(LOCATIONS)))
        else:
            event.location = Calendar.Location.getLocation(view, random.choice(LOCATIONS))



    event.importance = random.choice(IMPORTANCE)
    return event


TITLES = [u"reading list", u"restaurant recommendation", u"vacation ideas",
          u"grocery list", u"gift ideas", u"life goals", u"fantastic recipe",
          u"garden plans", u"funny joke", u"story idea", u"poem"]

EVENT, TASK, BOTH = range(2, 5)
M_TEXT  = u"This is a test email message"
M_EVENT = u" that has been stamped as a Calendar Event"
M_TASK  = u" that has been stamped as a Task"
M_BOTH  = u" that has been stamped as a Task and a Calendar Event"
M_FROM  = None

def GenerateMailMessage(view, tzinfo=None):
    #XXX [i18n] need to add i18n tests for to and from address
    global M_FROM
    message  = Mail.MailMessage(view=view)
    body     = M_TEXT

    outbound = random.randint(0, 1)
    type     = random.randint(1, 8)
    numTo    = random.randint(1, 3)

    if M_FROM is None:
        M_FROM = GenerateCalendarParticipant(view)

    message.fromAddress = M_FROM

    for num in range(numTo):
        message.toAddress.append(GenerateCalendarParticipant(view))

    message.subject  = random.choice(TITLES)

    if TEST_I18N:
        message.subject = addSurrogatePairToText(message.subject)

    message.dateSent = datetime.now()



    if outbound:
        acc = Mail.getCurrentSMTPAccount(view)[0]
        message.outgoingMessage(acc)

        """Make the Message appear as if it has already been sent"""
        message.deliveryExtension.sendSucceeded()

    else:
        acc = Mail.getCurrentMailAccount(view)
        message.incomingMessage(acc)

    if type == EVENT:
        message.StampKind('add', Calendar.CalendarEventMixin.getKind(message.itsView))
        body += M_EVENT

    if type == TASK:
        message.StampKind('add', pim.TaskMixin.getKind(message.itsView))
        body += M_TASK

    if type == BOTH:
        message.StampKind('add', pim.TaskMixin.getKind(message.itsView))
        message.StampKind('add', Calendar.CalendarEventMixin.getKind(message.itsView))
        body += M_BOTH

    if TEST_I18N:
        body = addSurrogatePairToText(body)

    message.body = message.getAttributeAspect('body', 'type').makeValue(body)

    return message

def GenerateNote(view, tzinfo=None):
    """ Generate one Note item """
    note = pim.Note(view=view)
    note.displayName = random.choice(TITLES)

    if TEST_I18N:
        note.displayName = addSurrogatePairToText(note.displayName)

    delta = timedelta(days=random.randint(0, 5),
                      hours=random.randint(0, 24))
    note.createdOn = datetime.now(tzinfo) + delta
    return note

def GenerateTask(view, tzinfo=None):
    """ Generate one Task item """
    task = pim.Task(view=view)
    delta = timedelta(days=random.randint(0, 5),
                      hours=random.randint(0, 24))
    task.dueDate = datetime.today() + delta
    task.displayName = random.choice(TITLES)

    if TEST_I18N:
        task.displayName = addSurrogatePairToText(task.displayName)

    return task

def GenerateEventTask(view, days=30, tzinfo=None):
    """ Generate one Task/Event stamped item """
    event = GenerateCalendarEvent(view, days, tzinfo=tzinfo)
    event.StampKind('add', pim.TaskMixin.getKind(event.itsView))
    return event

DOMAIN_LIST = [u'flossrecycling.com', u'flossresearch.org', u'rosegardens.org',
               u'electricbagpipes.com', u'facelessentity.com', u'example.com',
               u'example.org', u'example.net', u'hangarhonchos.org', u'ludditesonline.net']

FIRSTNAMES = [u'Alec', u'Aleks', u'Alexis', u'Amy', u'Andi', u'Andy', u'Aparna',
              u'Bart', u'Blue', u'Brian', u'Bryan', u'Caroline', u'Cedric', u'Chao', u'Chris',
              u'David', u'Donn', u'Ducky', u'Dulcy', u'Erin', u'Esther',
              u'Freada', u'Grant', u'Greg', u'Heikki', u'Hilda',
              u'Jed', u'John', u'Jolyn', u'Jurgen', u'Jae Hee',
              u'Katie', u'Kevin', u'Lisa', u'Lou',
              u'Michael', u'Mimi', u'Mitch', u'Mitchell', u'Morgen',
              u'Pieter', u'Robin', u'Stefanie', u'Stuart', u'Suzette',
              u'Ted', u'Trudy', u'William']

LASTNAMES = [u'Anderson', u'Baillie', u'Baker', u'Botz', u'Brown', u'Burgess',
             u'Capps', u'Cerneka', u'Chang', u'Decker', u'Decrem', u'Denman', u'Desai', u'Dunn', u'Dusseault',
             u'Figueroa', u'Flett', u'Gamble', u'Gravelle',
             u'Hartsook', u'Haurnesser', u'Hernandez', u'Hertzfeld', u'Humpa',
             u'Kapor', u'Klein', 'Kim', u'Lam', u'Leung', u'McDevitt', u'Montulli', u'Moseley',
             u'Okimoto', u'Parlante', u'Parmenter', u'Rosa',
             u'Sagen', u'Sciabica', u'Sherwood', u'Skinner', u'Stearns', u'Sun', u'Surovell',
             u'Tauber', u'Totic', u'Toivonen', u'Toy', u'Tsurutome', u'Vajda', u'Yin']

COLLECTION_NAMES = [u'Scratchings', u'Home', u'Work', u'OSAF', u'Kids', u'School', u'Book club', u'Wine club', u'Karate', u'Knitting', u'Soccer', u'Chandler', u'Cosmo', u'Scooby', u'Choir', u'Movies', u'Snowball', u'Lassie', u'Humor', u'Odds n Ends', u'BayCHI', u'OSCON', u'IETF', u'Financial', u'Medical', u'Philanthropy']

PHONETYPES = [u'cell', u'voice', u'fax', u'pager']

#area codes not listed as valid at http://www.cs.ucsd.edu/users/bsy/area.html
AREACODES = [311,411,555,611,811,324,335]

def GeneratePhoneNumber():
    areaCode = random.choice(AREACODES)
    exchange = random.randint(220, 999)
    number = random.randint(1000, 9999)
    return u"(%3d) %3d-%4d" % (areaCode, exchange, number)

def GenerateEmailAddress(name):
    domainName = random.choice(DOMAIN_LIST)
    handle = random.choice([name.firstName, name.lastName])
    return u"%s@%s" % (handle.lower(), domainName)

def GenerateEmailAddresses(view, name):
    list = []
    for i in range(random.randint(1, 2)):
        email = Mail.EmailAddress(view=view)
        email.emailAddress = GenerateEmailAddress(name)
        list.append(email)
    return list

def GenerateContactName(view):
    name = pim.ContactName(view=view)
    name.firstName = random.choice(FIRSTNAMES)
    name.lastName = random.choice(LASTNAMES)

    if TEST_I18N:
        name.firstName = addSurrogatePairToText(name.firstName)
        name.lastName = addSurrogatePairToText(name.lastName)

    return name

def GenerateContact(view):
    contact = pim.Contact(view=view)
    contact.contactName = GenerateContactName(view)
    return contact

def GenerateCollection(view, postToView=None, existingNames=None):
    collection = pim.ListCollection(view=view, chooseColor=True)
    
    while True:
        # Find a name that isn't already in use
        potentialName = random.choice(COLLECTION_NAMES)

        if TEST_I18N:
            potentialName = addSurrogatePairToText(potentialName)

        if existingNames is None or potentialName not in existingNames:
            collection.displayName = potentialName
            if existingNames is not None:
                existingNames.append(potentialName)
            break
        
    if postToView is not None:
        postToView.postEventByName ('AddToSidebarWithoutCopyingOrCommiting', {'items': [ collection ] })
    return collection


def GenerateItems(view, count, function, collections=[], *args, **dict):
    """ 
    Generate 'count' content items using the given function (and args), and
    add them to a subset of the given collections (if given)
    """
    
    # At most, we'll add each item to a third of the collections, if we were given any
    maxCollCount = (len(collections) / 3)
    
    results = []
    for index in range(count):
        newItem = function(view, *args, **dict)
        
        if maxCollCount > 0:
            for index in range(random.randint(0, maxCollCount)):
                collections[random.randint(0, len(collections)-1)].add(newItem)    
            
        results.append(newItem)

    return results

def GenerateAllItems(view, count, mainView=None, sidebarCollection=None):
    """ Generate a bunch of items of several types, for testing. """
    
    # Generate some item collections to put them in.
    existingNames = sidebarCollection is not None and [ existingCollection.displayName for existingCollection in sidebarCollection] or []
    collections = GenerateItems(view, 6, GenerateCollection, [], mainView, existingNames)
    
    items = []
    defaultTzinfo = ICUtzinfo.getDefault()
    for fn in GenerateMailMessage, GenerateNote, GenerateCalendarEvent, GenerateTask, GenerateEventTask: # GenerateContact omitted.
        def newFn(*args, **keywds):
            keywds['tzinfo'] = defaultTzinfo
            return fn(*args, **keywds)
        items.append(GenerateItems(view, count, newFn, collections))

    view.commit() 
    return items
