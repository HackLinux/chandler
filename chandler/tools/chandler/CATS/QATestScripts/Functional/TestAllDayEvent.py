import util.QAUITestAppLib as QAUITestAppLib
import os

filePath = os.getenv('CATSREPORTDIR')
if not filePath:
    filePath = os.getcwd()

#initialization
fileName = "TestAllDayEvent.log"
logger = QAUITestAppLib.QALogger(os.path.join(filePath, fileName),"TestAllDayEvent")
event = QAUITestAppLib.UITestItem("Event", logger)

#action
event.SetAllDay(True)

#verification
event.Check_DetailView({"AllDay":True})
event.Check_Object({"AllDay":True})

#cleaning
logger.Close()
