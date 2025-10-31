from director import callbacks
from collections import OrderedDict
import re

def cleanPropertyName(s):
    """
    Generate a valid python property name by replacing all non-alphanumeric characters with underscores and adding an initial underscore if the first character is a digit
    """
    return re.sub(r'\W|^(?=\d)','_',s).lower()


class PropertyAttributes(object):
    """Property attributes for controlling how properties are displayed/edited."""

    def __init__(self, **kwargs):
        self.decimals = 5
        self.minimum = -1e4
        self.maximum = 1e4
        self.singleStep = 1
        self.hidden = False
        self.enumNames = None
        self.readOnly = False
        
        # Override with any provided kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        # Allow dict-like access for compatibility
        self._dict = {
            'decimals': self.decimals,
            'minimum': self.minimum,
            'maximum': self.maximum,
            'singleStep': self.singleStep,
            'hidden': self.hidden,
            'enumNames': self.enumNames,
            'readOnly': self.readOnly,
        }
    
    def __getitem__(self, key):
        """Allow dict-like access."""
        return getattr(self, key, None)
    
    def __setitem__(self, key, value):
        """Allow dict-like assignment."""
        setattr(self, key, value)
        if key in self._dict:
            self._dict[key] = value


def fromQColor(propertyName, propertyValue):
    """Convert QColor to list if needed."""
    from qtpy import QtGui
    if isinstance(propertyValue, QtGui.QColor):
        return [propertyValue.red()/255.0, propertyValue.green()/255.0, propertyValue.blue()/255.0]
    else:
        return propertyValue

def toQProperty(propertyName, propertyValue):
    """Convert property value to Qt-compatible format."""
    from qtpy import QtGui
    if 'color' in propertyName.lower() and isinstance(propertyValue, (list, tuple)) and len(propertyValue) == 3:
        return QtGui.QColor(int(propertyValue[0]*255.0), int(propertyValue[1]*255.0), int(propertyValue[2]*255.0))
    else:
        return propertyValue


class PropertySet(object):

    PROPERTY_CHANGED_SIGNAL = 'PROPERTY_CHANGED_SIGNAL'
    PROPERTY_ADDED_SIGNAL = 'PROPERTY_ADDED_SIGNAL'
    PROPERTY_ATTRIBUTE_CHANGED_SIGNAL = 'PROPERTY_ATTRIBUTE_CHANGED_SIGNAL'

    def __getstate__(self):
        d = dict(_properties=self._properties, _attributes=self._attributes)
        return d

    def __setstate__(self, state):
        self.__init__()
        attrs = state['_attributes']
        for propName, propValue in list(state['_properties'].items()):
            self.addProperty(propName, propValue, attributes=attrs.get(propName))

    def __init__(self):
        self.callbacks = callbacks.CallbackRegistry([self.PROPERTY_CHANGED_SIGNAL,
                                                     self.PROPERTY_ADDED_SIGNAL,
                                                     self.PROPERTY_ATTRIBUTE_CHANGED_SIGNAL])

        self._properties = OrderedDict()
        self._attributes = {}
        self._alternateNames = {}

    def propertyNames(self):
        return list(self._properties.keys())

    def hasProperty(self, propertyName):
        return propertyName in self._properties

    def connectPropertyChanged(self, func):
        return self.callbacks.connect(self.PROPERTY_CHANGED_SIGNAL, func)

    def disconnectPropertyChanged(self, callbackId):
        self.callbacks.disconnect(callbackId)

    def connectPropertyAdded(self, func):
        return self.callbacks.connect(self.PROPERTY_ADDED_SIGNAL, func)

    def disconnectPropertyAdded(self, callbackId):
        self.callbacks.disconnect(callbackId)

    def connectPropertyAttributeChanged(self, func):
        return self.callbacks.connect(self.PROPERTY_ATTRIBUTE_CHANGED_SIGNAL, func)

    def disconnectPropertyAttributeChanged(self, callbackId):
        self.callbacks.disconnect(callbackId)

    def getProperty(self, propertyName):
        return self._properties[propertyName]

    def getPropertyEnumValue(self, propertyName):
        attributes = self._attributes[propertyName]
        return attributes.enumNames[self._properties[propertyName]]

    def removeProperty(self, propertyName):
        del self._properties[propertyName]
        del self._attributes[propertyName]
        del self._alternateNames[cleanPropertyName(propertyName)]

    def addProperty(self, propertyName, propertyValue, attributes=None, index=None):
        alternateName = cleanPropertyName(propertyName)
        if propertyName not in self._properties and alternateName in self._alternateNames:
            raise ValueError('Adding this property would conflict with a different existing property with alternate name {:s}'.format(alternateName))
        propertyValue = fromQColor(propertyName, propertyValue)
        self._properties[propertyName] = propertyValue
        self._attributes[propertyName] = attributes or PropertyAttributes()
        self._alternateNames[alternateName] = propertyName
        if index is not None:
            self.setPropertyIndex(propertyName, index)
        self.callbacks.process(self.PROPERTY_ADDED_SIGNAL, self, propertyName)

    def setPropertyIndex(self, propertyName, newIndex):
        assert self.hasProperty(propertyName)
        currentIndex = list(self._properties.keys()).index(propertyName)
        inds = list(range(len(self._properties)))
        inds.remove(currentIndex)
        inds.insert(newIndex, currentIndex)
        items = list(self._properties.items())
        self._properties = OrderedDict([items[i] for i in inds])

    def setProperty(self, propertyName, propertyValue):
        previousValue = self._properties[propertyName]
        propertyValue = fromQColor(propertyName, propertyValue)
        if propertyValue == previousValue:
          return

        names = self.getPropertyAttribute(propertyName, 'enumNames')
        if names and type(propertyValue) != int:
            propertyValue = names.index(propertyValue)

        self._properties[propertyName] = propertyValue
        self.callbacks.process(self.PROPERTY_CHANGED_SIGNAL, self, propertyName)

    def getPropertyAttribute(self, propertyName, propertyAttribute):
        attributes = self._attributes[propertyName]
        return attributes[propertyAttribute]

    def setPropertyAttribute(self, propertyName, propertyAttribute, value):
        attributes = self._attributes[propertyName]
        if attributes[propertyAttribute] != value:
            attributes[propertyAttribute] = value
            self.callbacks.process(self.PROPERTY_ATTRIBUTE_CHANGED_SIGNAL, self, propertyName, propertyAttribute)

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError as exc:
            alternateNames = object.__getattribute__(self, '_alternateNames')
            if name in alternateNames:
                return object.__getattribute__(self, 'getProperty')(alternateNames[name])
            else:
                raise exc


class PropertyPanelHelper(object):
    """Helper class for adding properties to a panel (stub for now)."""
    
    @staticmethod
    def addPropertiesToPanel(properties, panel, propertyNamesToAdd=None):
        """Add properties to the panel (stub implementation)."""
        # For now, just a stub - will be implemented when PropertiesPanel is ready
        pass


class PropertyPanelConnector(object):
    """Connector between PropertySet and PropertiesPanel (stub for now)."""
    
    def __init__(self, propertySet, propertiesPanel, propertyNamesToAdd=None):
        self.propertySet = propertySet
        self.propertyNamesToAdd = propertyNamesToAdd
        self.propertiesPanel = propertiesPanel
        self.connections = []
        # For now, don't connect anything since PropertiesPanel is a dummy
        # self.connections.append(self.propertySet.connectPropertyAdded(self._onPropertyAdded))
        # self.connections.append(self.propertySet.connectPropertyChanged(self._onPropertyChanged))
        # self.connections.append(self.propertySet.connectPropertyAttributeChanged(self._onPropertyAttributeChanged))
    
    def cleanup(self):
        """Clean up connections."""
        for connection in self.connections:
            self.propertySet.callbacks.disconnect(connection)
        self.connections = []

