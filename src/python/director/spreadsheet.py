
from PythonQt import QtCore, QtGui
import functools

from director import applogic as app

_spreadsheetView = None
def getSpreadsheetView():
    return _spreadsheetView


def setSpreadsheetColumnData(columnIndex, name, data):

    sv = getSpreadsheetView()
    model = sv.model()

    model.item(0, columnIndex).setText(name)
    for i, value in enumerate(data):
          model.item(i + 1, columnIndex).setText(value)


def updateSpreadsheetPoses(poseCollection, poseName=None):

    poseMap = poseCollection.map()
    for i, poseName in enumerate(sorted(poseMap.keys())):
        setSpreadsheetColumnData(i + 3, poseName, poseMap[poseName])


def setSpreadsheetDataFromCollection(columnIndex, dataCollection, dataKey):
    setSpreadsheetColumnData(columnIndex, dataKey, collection.map()[dataKey])


def initJointNamesColumns(jointNames):
    setSpreadsheetColumnData(0, 'joint_names', jointNames)


def init(jointNames, poseCollection, costCollection):

    global _spreadsheetView
    _spreadsheetView = app.getViewManager().createView('Spreadsheet View', 'Spreadsheet View')

    initJointNamesColumns(jointNames)

    updateMethod = functools.partial(updateSpreadsheetPoses, poseCollection)
    poseCollection.connect('itemChanged(const QString&)', updateMethod)
    poseCollection.connect('itemAdded(const QString&)', updateMethod)
    poseCollection.connect('itemRemoved(const QString&)', updateMethod)

    updateMethod()

