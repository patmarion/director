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


class PropertySet(object):

    PROPERTY_CHANGED_SIGNAL = 'PROPERTY_CHANGED_SIGNAL'
    PROPERTY_ADDED_SIGNAL = 'PROPERTY_ADDED_SIGNAL'
    PROPERTY_REMOVED_SIGNAL = 'PROPERTY_REMOVED_SIGNAL'
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
                                                     self.PROPERTY_REMOVED_SIGNAL,
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

    def connectPropertyRemoved(self, func):
        return self.callbacks.connect(self.PROPERTY_REMOVED_SIGNAL, func)

    def disconnectPropertyRemoved(self, callbackId):
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
        if propertyName not in self._properties:
            return
        del self._properties[propertyName]
        del self._attributes[propertyName]
        del self._alternateNames[cleanPropertyName(propertyName)]
        self.callbacks.process(self.PROPERTY_REMOVED_SIGNAL, self, propertyName)

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
    
    def __setattr__(self, name, value):
        """Allow setting properties via alternate names."""
        # First, check if this is a real attribute (one that exists or is being initialized)
        # We need to check this carefully to avoid infinite recursion
        
        # Check if this is a protected/private attribute or an internal attribute
        if name.startswith('_') or name in ['callbacks', '_properties', '_attributes', '_alternateNames']:
            object.__setattr__(self, name, value)
            return
        
        # Try to get the attribute - if it exists, set it normally
        try:
            # If we can get it, it's a real attribute
            object.__getattribute__(self, name)
            object.__setattr__(self, name, value)
            return
        except AttributeError:
            # Attribute doesn't exist, check if it's an alternate property name
            try:
                alternateNames = object.__getattribute__(self, '_alternateNames')
                if name in alternateNames:
                    # Found as alternate name, set the property
                    propertyName = alternateNames[name]
                    object.__getattribute__(self, 'setProperty')(propertyName, value)
                    return
                else:
                    # Not found, raise AttributeError
                    raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
            except AttributeError:
                # _alternateNames doesn't exist yet (during __init__), just set normally
                object.__setattr__(self, name, value)