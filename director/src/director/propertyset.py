from collections import OrderedDict
import copy
import re
from typing import Any, Dict

from director import callbacks


def cleanPropertyName(s):
    """
    Generate a valid python property name by replacing all non-alphanumeric characters with underscores and adding an initial underscore if the first character is a digit
    """
    return re.sub(r"\W|^(?=\d)", "_", s).lower()


class PropertyAttributes(object):
    """Property attributes for controlling how properties are displayed/edited."""

    _FIELDS = (
        "decimals",
        "minimum",
        "maximum",
        "singleStep",
        "hidden",
        "enumNames",
        "readOnly",
    )

    def __init__(self, **kwargs):
        defaults = {
            "decimals": 5,
            "minimum": -1e4,
            "maximum": 1e4,
            "singleStep": 1,
            "hidden": False,
            "enumNames": None,
            "readOnly": False,
        }
        defaults.update(kwargs)
        for field in self._FIELDS:
            setattr(self, field, defaults.get(field))

    def __getitem__(self, key):
        """Allow dict-like access."""
        return getattr(self, key, None)

    def __setitem__(self, key, value):
        """Allow dict-like assignment."""
        setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        return {field: copy.deepcopy(getattr(self, field)) for field in self._FIELDS}

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "PropertyAttributes":
        if not data:
            return cls()
        return cls(**data)


def fromQColor(propertyName, propertyValue):
    """Convert QColor to list if needed."""
    from qtpy import QtGui

    if isinstance(propertyValue, QtGui.QColor):
        return [propertyValue.red() / 255.0, propertyValue.green() / 255.0, propertyValue.blue() / 255.0]
    else:
        return propertyValue


class PropertySet(object):
    PROPERTY_CHANGED_SIGNAL = "PROPERTY_CHANGED_SIGNAL"
    PROPERTY_ADDED_SIGNAL = "PROPERTY_ADDED_SIGNAL"
    PROPERTY_REMOVED_SIGNAL = "PROPERTY_REMOVED_SIGNAL"
    PROPERTY_ATTRIBUTE_CHANGED_SIGNAL = "PROPERTY_ATTRIBUTE_CHANGED_SIGNAL"

    def __init__(self):
        self.callbacks = callbacks.CallbackRegistry(
            [
                self.PROPERTY_CHANGED_SIGNAL,
                self.PROPERTY_ADDED_SIGNAL,
                self.PROPERTY_REMOVED_SIGNAL,
                self.PROPERTY_ATTRIBUTE_CHANGED_SIGNAL,
            ]
        )

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

    def connectPropertyValueChanged(self, propertyName, func):
        def onPropertyChanged(propertySet, changedPropertyName):
            if changedPropertyName == propertyName:
                func(propertySet.getProperty(propertyName))

        return self.connectPropertyChanged(onPropertyChanged)

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
            raise ValueError(
                "Adding this property would conflict with a different existing property with alternate name {:s}".format(
                    alternateName
                )
            )
        attrs = self._coerce_attributes(attributes)
        propertyValue = self._normalize_property_value(
            propertyName, propertyValue, existing_value=None, attributes=attrs
        )
        self._properties[propertyName] = propertyValue
        self._attributes[propertyName] = attrs
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
        attrs = self._attributes[propertyName]
        propertyValue = self._normalize_property_value(
            propertyName, propertyValue, existing_value=previousValue, attributes=attrs
        )
        if propertyValue == previousValue:
            return

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
            alternateNames = object.__getattribute__(self, "_alternateNames")
            if name in alternateNames:
                return object.__getattribute__(self, "getProperty")(alternateNames[name])
            else:
                raise exc

    def __setattr__(self, name, value):
        """Allow setting properties via alternate names."""
        # First, check if this is a real attribute (one that exists or is being initialized)
        # We need to check this carefully to avoid infinite recursion

        # Check if this is a protected/private attribute or an internal attribute
        if name.startswith("_") or name in ["callbacks", "_properties", "_attributes", "_alternateNames"]:
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
                alternateNames = object.__getattribute__(self, "_alternateNames")
                if name in alternateNames:
                    # Found as alternate name, set the property
                    propertyName = alternateNames[name]
                    object.__getattribute__(self, "setProperty")(propertyName, value)
                    return
                else:
                    # Not found, raise AttributeError
                    raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
            except AttributeError:
                # _alternateNames doesn't exist yet (during __init__), just set normally
                object.__setattr__(self, name, value)

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def get_state_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable snapshot of properties and attributes."""
        properties_copy = OrderedDict()
        for name, value in self._properties.items():
            properties_copy[name] = copy.deepcopy(value)

        attributes_copy = {name: attrs.to_dict() for name, attrs in self._attributes.items()}
        return {"properties": properties_copy, "attributes": attributes_copy}

    def restore_from_state_dict(self, state: Dict[str, Any], merge: bool = True, verbose: bool = False):
        """Restore properties/attributes from a state dict."""
        properties = state.get("properties") or {}
        attributes = state.get("attributes") or {}

        if not merge:
            if self._properties:
                raise AssertionError("PropertySet.restore_from_state_dict(merge=False) requires an empty PropertySet.")
            for name, value in properties.items():
                attr_dict = attributes.get(name)
                self.addProperty(name, value, attributes=PropertyAttributes.from_dict(attr_dict))
            return

        for name, value in properties.items():
            attr_dict = attributes.get(name)
            if not self.hasProperty(name):
                self.addProperty(name, value, attributes=PropertyAttributes.from_dict(attr_dict))
                continue

            if attr_dict and verbose:
                self._log_attribute_mismatches(name, attr_dict)

            self._assert_value_compatible(name, value)
            new_value = copy.deepcopy(value)
            self._warn_if_out_of_bounds(name, new_value, verbose)
            self.setProperty(name, new_value)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _coerce_attributes(self, attributes) -> PropertyAttributes:
        if attributes is None:
            return PropertyAttributes()
        if isinstance(attributes, PropertyAttributes):
            return attributes
        if isinstance(attributes, dict):
            return PropertyAttributes.from_dict(attributes)
        raise TypeError(f"Unsupported attributes type: {type(attributes)}")

    def _normalize_property_value(
        self,
        propertyName: str,
        propertyValue: Any,
        existing_value: Any | None,
        attributes: PropertyAttributes | None = None,
    ) -> Any:
        value = fromQColor(propertyName, propertyValue)
        if attributes and attributes.enumNames:
            value = self._coerce_enum_value(propertyName, value, attributes.enumNames)
        if hasattr(value, "tolist"):
            try:
                value = value.tolist()
            except Exception:
                pass
        if isinstance(value, (list, tuple)):
            normalized = tuple(value)
        else:
            normalized = value

        if existing_value is None:
            return normalized
        return self._cast_like_existing(propertyName, normalized, existing_value)

    def _log_attribute_mismatches(self, propertyName: str, saved_attrs: Dict[str, Any]):
        current_attrs = self._attributes[propertyName]
        mismatches = []
        for field in PropertyAttributes._FIELDS:
            saved_value = saved_attrs.get(field, getattr(current_attrs, field))
            current_value = getattr(current_attrs, field)
            if saved_value != current_value:
                mismatches.append(f"{field}: saved={saved_value!r} current={current_value!r}")
        if mismatches:
            print(f"[PropertySet] Attribute differences for '{propertyName}': " + "; ".join(mismatches))

    def _assert_value_compatible(self, propertyName: str, new_value: Any):
        existing_value = self._properties[propertyName]
        if isinstance(existing_value, tuple):
            if not isinstance(new_value, (list, tuple)):
                raise ValueError(f"Property '{propertyName}' expects sequence value.")
            if len(existing_value) != len(new_value):
                raise ValueError(f"Property '{propertyName}' sequence length mismatch.")
        elif isinstance(existing_value, (int, float, bool)):
            if not isinstance(new_value, (int, float, bool)):
                raise ValueError(f"Property '{propertyName}' numeric type mismatch.")
        else:
            if not isinstance(new_value, type(existing_value)):
                raise ValueError(f"Property '{propertyName}' type mismatch.")

    def _warn_if_out_of_bounds(self, propertyName: str, value: Any, verbose: bool):
        if not verbose:
            return
        attrs = self._attributes[propertyName]
        if isinstance(value, (int, float)):
            if value < attrs.minimum or value > attrs.maximum:
                print(
                    f"[PropertySet] Value {value} for '{propertyName}' is outside [{attrs.minimum}, {attrs.maximum}]."
                )
        elif isinstance(value, (list, tuple)) and value and isinstance(value[0], (int, float)):
            for idx, component in enumerate(value):
                if component < attrs.minimum or component > attrs.maximum:
                    print(
                        f"[PropertySet] Component {idx} value {component} for '{propertyName}' is outside [{attrs.minimum}, {attrs.maximum}]."
                    )
                    break

    def _cast_like_existing(self, propertyName: str, new_value: Any, existing_value: Any):
        if isinstance(existing_value, tuple):
            if not isinstance(new_value, (list, tuple)):
                raise ValueError(f"Property '{propertyName}' expects sequence value.")
            if len(existing_value) != len(new_value):
                raise ValueError(f"Property '{propertyName}' sequence length mismatch.")
            return tuple(
                self._cast_scalar(propertyName, component, existing_component)
                for component, existing_component in zip(new_value, existing_value)
            )

        if isinstance(existing_value, (int, float)) and not isinstance(existing_value, bool):
            if not isinstance(new_value, (int, float)):
                raise ValueError(f"Property '{propertyName}' numeric type mismatch.")
            return float(new_value) if isinstance(existing_value, float) else type(existing_value)(new_value)

        if isinstance(existing_value, bool):
            if not isinstance(new_value, (bool, int)):
                raise ValueError(f"Property '{propertyName}' bool type mismatch.")
            return bool(new_value)

        if isinstance(existing_value, str):
            if not isinstance(new_value, str):
                raise ValueError(f"Property '{propertyName}' requires string value.")
            return new_value

        if type(new_value) is not type(existing_value):
            raise ValueError(f"Property '{propertyName}' type mismatch.")
        return new_value

    def _cast_scalar(self, propertyName: str, value: Any, existing_component: Any):
        if isinstance(existing_component, (int, float)) and not isinstance(existing_component, bool):
            if not isinstance(value, (int, float)):
                raise ValueError(f"Property '{propertyName}' sequence numeric mismatch.")
            return float(value) if isinstance(existing_component, float) else type(existing_component)(value)

        if isinstance(existing_component, bool):
            if not isinstance(value, (bool, int)):
                raise ValueError(f"Property '{propertyName}' sequence bool mismatch.")
            return bool(value)

        if type(value) is not type(existing_component):
            raise ValueError(f"Property '{propertyName}' sequence type mismatch.")
        return value

    def _coerce_enum_value(self, propertyName: str, value: Any, enum_names):
        if isinstance(value, int):
            if not 0 <= value < len(enum_names):
                raise ValueError(f"Property '{propertyName}' enum index out of range.")
            return value
        if isinstance(value, str):
            if value not in enum_names:
                raise ValueError(f"Property '{propertyName}' enum value '{value}' invalid.")
            return enum_names.index(value)
        raise ValueError(f"Property '{propertyName}' enum expects str or int value.")
