import os
import re
from collections import defaultdict
import PythonQt
from PythonQt import QtCore, QtGui
from director.propertyset import PropertySet, PropertyAttributes, PropertyPanelHelper, PropertyPanelConnector
from director import callbacks
import functools

class Icons(object):

  Directory = int(QtGui.QStyle.SP_DirIcon)
  Axes = ':/images/axes_icon.png'
  Eye = ':/images/eye_icon.png'
  EyeOff = ':/images/eye_icon_gray.png'
  Matlab = ':/images/matlab_logo.png'
  Robot = ':/images/robot_icon.png'
  Hammer = ':/images/hammer_icon.png'
  Laser = ':/images/laser_icon.jpg'
  Feet = ':/images/feet.png'
  Hand = ':/images/claw.png'
  Octomap = ':/images/octomap.jpg'
  Collections = ':/images/rubix_cube.jpg'

  @staticmethod
  @functools.lru_cache()
  def getIcon(iconId):
      '''
      Return a QIcon given an icon id as a string or int.
      '''
      if type(iconId) == int:
          return QtGui.QApplication.style().standardIcon(iconId)
      else:
          return QtGui.QIcon(iconId)

class ObjectModelItem(object):

    REMOVED_FROM_OBJECT_MODEL = 'REMOVED_FROM_OBJECT_MODEL'

    def __getstate__(self):
        #print 'getstate called on:', self
        d = dict(properties=self.properties)
        return d

    def __setstate__(self, state):
        #print 'setstate called on:', self
        self._tree = None
        self.properties = state['properties']

    def __init__(self, name, icon=Icons.Robot, properties=None):

        #print 'init called on:', self
        self._tree = None
        self.actionDelegates = []
        self.callbacks = callbacks.CallbackRegistry([self.REMOVED_FROM_OBJECT_MODEL])
        self.properties = properties or PropertySet()
        self.properties.connectPropertyChanged(self._onPropertyChanged)
        self.properties.connectPropertyAdded(self._onPropertyAdded)
        self.properties.connectPropertyAttributeChanged(self._onPropertyAttributeChanged)

        self.addProperty('Icon', icon, attributes=PropertyAttributes(hidden=True))
        self.addProperty('Deletable', True, attributes=PropertyAttributes(hidden=True))
        self.addProperty('Name', name, attributes=PropertyAttributes(hidden=True))

    def setIcon(self, icon):
        self.setProperty('Icon', icon)

    def propertyNames(self):
        return self.properties.propertyNames()

    def hasProperty(self, propertyName):
        return self.properties.hasProperty(propertyName)

    def getProperty(self, propertyName):
        return self.properties.getProperty(propertyName)

    def getPropertyEnumValue(self, propertyName):
        return self.properties.getPropertyEnumValue(propertyName)

    def addProperty(self, propertyName, propertyValue, attributes=None, index=None):
        self.properties.addProperty(propertyName, propertyValue, attributes, index)

    def removeProperty(self, propertyName):
        self.properties.removeProperty(propertyName)

    def setProperty(self, propertyName, propertyValue):
        self.properties.setProperty(propertyName, propertyValue)

    def getPropertyAttribute(self, propertyName, propertyAttribute):
        return self.properties.getPropertyAttribute(propertyName, propertyAttribute)

    def setPropertyAttribute(self, propertyName, propertyAttribute, value):
        self.properties.setPropertyAttribute(propertyName, propertyAttribute, value)

    def _onPropertyChanged(self, propertySet, propertyName):
        if self._tree is not None:
            self._tree._onPropertyValueChanged(self, propertyName)

    def _onPropertyAdded(self, propertySet, propertyName):
        pass

    def _onPropertyAttributeChanged(self, propertySet, propertyName, propertyAttribute):
        pass

    def hasDataSet(self, dataSet):
        return False

    def hasActor(self, actor):
        return False

    def getActionNames(self):
        actions = ['Rename']
        for delegate in self.actionDelegates:
            delegateActions = delegate.getActionNames()
            if delegateActions:
                actions.append('')
                actions.extend(delegateActions)
        return actions

    def onAction(self, action):
        if action == 'Rename':
            name = self.getProperty('Name')

            inputDialog = QtGui.QInputDialog()
            inputDialog.setInputMode(inputDialog.TextInput)
            inputDialog.setLabelText('Name:')
            inputDialog.setWindowTitle('Enter name')
            inputDialog.setTextValue(name)
            result = inputDialog.exec_()

            if result:
                self.rename(inputDialog.textValue())

        for delegate in self.actionDelegates:
            consumed = delegate.onAction(self, action)
            if consumed:
                break

    def rename(self, name, renameChildren=True):
        oldName = self.getProperty('Name')
        if renameChildren:
            for child in self.children():
                childName = child.getProperty('Name')
                if childName.startswith(oldName):
                    child.setProperty('Name', name + childName[len(oldName):])
        self.setProperty('Name', name)

    def getObjectTree(self):
        return self._tree

    def onRemoveFromObjectModel(self):
        pass

    def connectRemovedFromObjectModel(self, func):
        return self.callbacks.connect(self.REMOVED_FROM_OBJECT_MODEL, func)

    def disconnectRemovedFromObjectModel(self, callbackId):
        self.callbacks.disconnect(callbackId)

    def parent(self):
        if self._tree is not None:
            return self._tree.getObjectParent(self)

    def children(self):
        if self._tree is not None:
            return self._tree.getObjectChildren(self)
        else:
            return []

    def findChild(self, name):
        if self._tree is not None:
            return self._tree.findChildByName(self, name)


class ContainerItem(ObjectModelItem):

    def __init__(self, name):
        ObjectModelItem.__init__(self, name, Icons.Directory)
        self.addProperty('Visible', True)

    def _onPropertyChanged(self, propertySet, propertyName):
        ObjectModelItem._onPropertyChanged(self, propertySet, propertyName)
        if propertyName == 'Visible':
            visible = self.getProperty(propertyName)
            for child in self.children():
                if child.hasProperty(propertyName):
                    child.setProperty(propertyName, visible)


class ObjectModelTree(object):

    ACTION_SELECTED = 'ACTION_SELECTED'
    OBJECT_ADDED = 'OBJECT_ADDED'
    OBJECT_CLICKED = 'OBJECT_CLICKED'
    SELECTION_CHANGED = 'SELECTION_CHANGED'

    def __init__(self):
        self.treeView = None
        self._propertiesPanel = None
        self._objectToItem = {}
        self._itemToObject = {}
        self._itemToName = {}
        self._nameToItems = defaultdict(set)
        self._blockSignals = False
        self._propertyConnector = None
        self.actions = []
        self.callbacks = callbacks.CallbackRegistry([
                            self.ACTION_SELECTED,
                            self.OBJECT_ADDED,
                            self.OBJECT_CLICKED,
                            self.SELECTION_CHANGED,
                            ])

    def getTreeWidget(self):
        return self.treeView

    def getTreeView(self):
        return self.treeView

    def getPropertiesPanel(self):
        return self._propertiesPanel

    def getObjectParent(self, obj):
        item = self._getItemForObject(obj)
        if item.parent():
            return self._getObjectForItem(item.parent())

    def getObjectChildren(self, obj):
        item = self._getItemForObject(obj)
        return [self._getObjectForItem(item.child(i)) for i in range(item.rowCount())]

    def getTopLevelObjects(self):
        return [self._getObjectForItem(self.itemModel.itemFromIndex(self.itemModel.index(i, 0)))
                  for i in range(self.itemModel.rowCount())]

    def getActiveObject(self):
        item = self._getSelectedItem()
        return self._itemToObject[item] if item is not None else None

    def getSelectedObject(self):
        return self.getActiveObject()

    def setSelectedObject(self, obj):
        self.setActiveObject(obj)

    def setActiveObject(self, obj):
        if not obj:
            self.clearSelection()
            return

        item = self._getItemForObject(obj)
        index = self.sortModel.mapFromSource(item.index())
        self.treeView.setCurrentIndex(index)
        self.treeView.scrollTo(index)

    def clearSelection(self):
        self.treeView.clearSelection()

    def getObjects(self):
        return list(self._itemToObject.values())

    def _getSelectedItem(self):
        inds = self.treeView.selectedIndexes()
        return self.itemModel.itemFromIndex(self.sortModel.mapToSource(inds[0])) if inds else None

    def _getItemForObject(self, obj):
        return self._objectToItem[obj]

    def _getObjectForItem(self, item):
        return self._itemToObject[item]

    def findObjectByName(self, name, parent=None):
        if parent:
            return self.findChildByName(parent, name)
        items = self._nameToItems.get(name)
        if items:
            return self._getObjectForItem(next(iter(items)))

    def findObjectByPath(self, path, separator='/'):
        return self.findObjectByPathList(path.split(separator))

    def findObjectByPathList(self, pathList):
        try:
            rootName = pathList[0]
        except IndexError:
            return None

        if not rootName:
            try:
                rootName = pathList[1]
            except IndexError:
                return None
            obj = self.findTopLevelObjectByName(rootName)
            pathList = pathList[2:]
        else:
            obj = self.findObjectByName(rootName)
            pathList = pathList[1:]
        if obj is None:
            return None
        for name in pathList:
            obj = obj.findChild(name)
            if obj is None:
                return None
        return obj

    def findChildByName(self, parent, name):
        parentItem = self._getItemForObject(parent) if parent else None
        for item in self._nameToItems[name]:
          if item.parent() == parentItem:
            return self._getObjectForItem(item)

    def findTopLevelObjectByName(self, name):
        for item in self._nameToItems[name]:
          if item.parent() is None:
            return self._getObjectForItem(item)

    def _onTreeSelectionChanged(self, selected, deselected):

        if self._propertyConnector:
          self._propertyConnector.cleanup()
          self._propertyConnector = None

        panel = self.getPropertiesPanel()
        panel.clear()

        obj = self.getActiveObject()
        if obj:
            self._propertyConnector = PropertyPanelConnector(obj.properties, panel)

        self.callbacks.process(self.SELECTION_CHANGED, self)

    def updateVisIcon(self, obj):
        if not obj.hasProperty('Visible'):
            return
        isVisible = obj.getProperty('Visible')
        objIndex = self._getItemForObject(obj).index()
        visIndex = self.itemModel.index(objIndex.row(), 1, objIndex.parent())
        visItem = self.itemModel.itemFromIndex(visIndex)
        visItem.setIcon(Icons.getIcon(Icons.Eye if isVisible else Icons.EyeOff))

    def updateObjectIcon(self, obj):
        item = self._getItemForObject(obj)
        item.setIcon(0, Icons.getIcon(obj.getProperty('Icon')))

    def updateObjectName(self, obj):
        item = self._getItemForObject(obj)
        oldName = self._itemToName[item]
        self._nameToItems[oldName].remove(item)
        name = obj.getProperty('Name')
        self._itemToName[item] = name
        self._nameToItems[name].add(item)
        item.setText(name)

    def _onPropertyValueChanged(self, obj, propertyName):

        if propertyName == 'Visible':
            self.updateVisIcon(obj)
        elif propertyName == 'Name':
            self.updateObjectName(obj)
        elif propertyName == 'Icon':
            self.updateObjectIcon(obj)

    def _onItemClicked(self, index):
        index = self.sortModel.mapToSource(index)
        objIndex = self.itemModel.index(index.row(), 0, index.parent())
        objItem = self.itemModel.itemFromIndex(objIndex)
        obj = self._itemToObject[objItem]

        if index.column() == 1 and obj.hasProperty('Visible'):
            obj.setProperty('Visible', not obj.getProperty('Visible'))
            self.updateVisIcon(obj)
        self.callbacks.process(self.OBJECT_CLICKED, self, obj)

    def _removeItemFromObjectModel(self, item):
        while item.rowCount():
            self._removeItemFromObjectModel(item.child(0, 0))

        obj = self._getObjectForItem(item)
        obj.callbacks.process(obj.REMOVED_FROM_OBJECT_MODEL, self, obj)
        obj.onRemoveFromObjectModel()
        obj._tree = None

        name = self._itemToName.pop(item)
        self._nameToItems[name].remove(item)
        del self._itemToObject[item]
        del self._objectToItem[obj]

        if item.parent():
            item.parent().removeRow(item.index().row())
        else:
            self.itemModel.removeRow(item.index().row())


    def removeFromObjectModel(self, obj):
        if obj:
            self._removeItemFromObjectModel(self._getItemForObject(obj))

    def addToObjectModel(self, obj, parentObj=None):
        assert obj._tree is None

        parentItem = self._getItemForObject(parentObj) if parentObj else None
        objName = obj.getProperty('Name')

        item = QtGui.QStandardItem(Icons.getIcon(obj.getProperty('Icon')), objName)
        item.setEditable(False)

        visItem = QtGui.QStandardItem()
        visItem.setEditable(False)

        obj._tree = self

        self._objectToItem[obj] = item
        self._itemToObject[item] = obj
        self._itemToName[item] = objName
        self._nameToItems[objName].add(item)

        if parentItem is None:
            self.itemModel.appendRow([item, visItem])
            self.treeView.expand(self.sortModel.mapFromSource(item.index()))
        else:
            parentItem.appendRow([item, visItem])

        self.updateVisIcon(obj)

        self.callbacks.process(self.OBJECT_ADDED, self, obj)


    def collapse(self, obj):
        item = self._getItemForObject(obj)
        self.treeView.collapse(self.sortModel.mapFromSource(item.index()))


    def expand(self, obj):
        item = self._getItemForObject(obj)
        self.treeView.expand(self.sortModel.mapFromSource(item.index()))


    def addContainer(self, name, parentObj=None):
        obj = ContainerItem(name)
        self.addToObjectModel(obj, parentObj)
        return obj


    def getOrCreateContainer(self, name, parentObj=None, collapsed=False):
        if parentObj:
            containerObj = parentObj.findChild(name)
        else:
            containerObj = self.findObjectByName(name)
        if not containerObj:
            containerObj = self.addContainer(name, parentObj)
            if collapsed:
                self.collapse(containerObj)
        return containerObj


    def _onShowContextMenu(self, clickPosition):
        obj = self.getActiveObject()
        if not obj:
            self._onTreeContextMenu(clickPosition)
        else:
            self._onObjectContextMenu(obj, clickPosition)


    def _showMenu(self, actions, clickPosition):

        if not actions:
            return None

        globalPos = self.getTreeWidget().viewport().mapToGlobal(clickPosition)

        menu = QtGui.QMenu()

        for name in actions:
            if not name:
                menu.addSeparator()
            else:
                menu.addAction(name)

        selectedAction = menu.exec_(globalPos)

        if selectedAction is not None:
            return selectedAction.text
        else:
            return None


    def _onTreeContextMenu(self, clickPosition):

        selectedAction = self._showMenu(self.actions, clickPosition)
        if selectedAction:
            self.callbacks.process(self.ACTION_SELECTED, self, selectedAction)


    def _onObjectContextMenu(self, obj, clickPosition):

        actions = list(obj.getActionNames())

        if obj.hasProperty('Deletable') and obj.getProperty('Deletable'):
            actions.append(None)
            actions.append('Remove')

        selectedAction = self._showMenu(actions, clickPosition)

        if selectedAction == 'Remove':
            self.removeFromObjectModel(obj)
        elif selectedAction:
            obj.onAction(selectedAction)

    def removeSelectedItems(self):
        inds = [self.sortModel.mapToSource(ind) for ind in self.getTreeWidget().selectedIndexes()]
        inds = [ind for ind in inds if ind.column() == 0]

        # we don't currently have multi select, so only one should be selected
        assert len(inds) == 1

        item = self.itemModel.itemFromIndex(inds[0])
        assert item
        obj = self._getObjectForItem(item)
        if (not obj.hasProperty('Deletable')) or obj.getProperty('Deletable'):
            self._removeItemFromObjectModel(item)

    def _filterEvent(self, obj, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Delete:
                self._eventFilter.setEventHandlerResult(True)
                self.removeSelectedItems()

    def connectSelectionChanged(self, func):
        return self.callbacks.connect(self.SELECTION_CHANGED, func)

    def disconnectSelectionChanged(self, callbackId):
        self.callbacks.disconnect(callbackId)

    def connectObjectAdded(self, func):
        return self.callbacks.connect(self.OBJECT_ADDED, func)

    def disconnectObjectAdded(self, callbackId):
        self.callbacks.disconnect(callbackId)

    def connectObjectClicked(self, func):
        return self.callbacks.connect(self.OBJECT_CLICKED, func)

    def disconnectObjectClicked(self, func):
        self.callbacks.disconnect(callbackId)

    def init(self, treeView, propertiesPanel):

        self._propertiesPanel = propertiesPanel
        propertiesPanel.clear()
        propertiesPanel.setBrowserModeToWidget()

        assert isinstance(treeView, QtGui.QTreeView)
        itemModel = QtGui.QStandardItemModel()
        itemModel.setColumnCount(2)
        itemModel.setHeaderData(0, QtCore.Qt.Horizontal, 'Name')
        itemModel.setHeaderData(1, QtCore.Qt.Horizontal, Icons.getIcon(Icons.Eye), 1)

        sortModel = QtGui.QSortFilterProxyModel()
        sortModel.setSourceModel(itemModel)

        treeView.setModel(sortModel)
        treeView.header().setStretchLastSection(False)

        try:
            setSectionResizeMode = treeView.header().setResizeMode
        except AttributeError:
            setSectionResizeMode = treeView.header().setSectionResizeMode

        setSectionResizeMode(0, QtGui.QHeaderView.Stretch)
        setSectionResizeMode(1, QtGui.QHeaderView.Fixed)
        treeView.setColumnWidth(1, 24)

        self.sortModel = sortModel
        self.itemModel = itemModel
        self.treeView = treeView

        treeView.selectionModel().connect('selectionChanged(const QItemSelection&, const QItemSelection&)', self._onTreeSelectionChanged)
        treeView.connect('clicked(const QModelIndex&)', self._onItemClicked)
        treeView.connect('customContextMenuRequested(const QPoint&)', self._onShowContextMenu)
        treeView.setContextMenuPolicy(PythonQt.QtCore.Qt.CustomContextMenu);

        self._eventFilter = PythonQt.dd.ddPythonEventFilter()
        self._eventFilter.addFilteredEventType(QtCore.QEvent.KeyPress)
        self._eventFilter.connect('handleEvent(QObject*, QEvent*)', self._filterEvent)
        treeView.installEventFilter(self._eventFilter)


#######################


_t = ObjectModelTree()

def getDefaultObjectModel():
    return _t

def getActiveObject():
    return _t.getActiveObject()

def setActiveObject(obj):
    _t.setActiveObject(obj)

getSelectedObject = getActiveObject
setSelectedObject = setActiveObject

def clearSelection():
    _t.clearSelection()

def getObjects():
    return _t.getObjects()

def getTopLevelObjects():
    return _t.getTopLevelObjects()

def findObjectByName(name, parent=None):
    return _t.findObjectByName(name, parent)

def findObjectByPathList(pathList):
    return _t.findObjectByPathList(pathList)

def findObjectByPath(path, separator='/'):
    return _t.findObjectByPath(path, separator)

def findTopLevelObjectByName(name):
    return _t.findTopLevelObjectByName(name)

def removeFromObjectModel(obj):
    _t.removeFromObjectModel(obj)

def addToObjectModel(obj, parentObj=None):
    _t.addToObjectModel(obj, parentObj)

def collapse(obj):
    _t.collapse(obj)

def expand(obj):
    _t.expand(obj)

def addContainer(name, parentObj=None):
    return _t.addContainer(name, parentObj)

def getOrCreateContainer(name, parentObj=None, collapsed=False):
    return _t.getOrCreateContainer(name, parentObj, collapsed)

def init(treeView=None, propertiesPanel=None):

    if _t.getTreeWidget():
        return

    treeView = treeView or QtGui.QTreeView()
    propertiesPanel = propertiesPanel or PythonQt.dd.ddPropertiesPanel()

    _t.init(treeView, propertiesPanel)

def addParentPropertySync(obj):
    parent = obj.parent()
    if parent is None:
        return
    if not hasattr(parent, '_syncedProperties'):
        def onPropertyChanged(propertySet, propertyName):
            if propertyName in parent._syncedProperties:
                for obj in parent.children():
                    obj.setProperty(propertyName, propertySet.getProperty(propertyName))
        parent._syncedProperties = set()
        parent.properties.connectPropertyChanged(onPropertyChanged)
    for propertyName in obj.properties.propertyNames():
        if propertyName == 'Name' or propertyName in parent._syncedProperties:
            continue
        parent._syncedProperties.add(propertyName)
        parent.properties.addProperty(propertyName, obj.properties.getProperty(propertyName), attributes=obj.properties._attributes[propertyName])

def addChildPropertySync(obj):
    children = obj.children()
    if children:
        addParentPropertySync(children[0])
