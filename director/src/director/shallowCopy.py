"""Utilities for shallow and deep copying VTK objects."""


def deepCopy(dataObj):
    """Create a deep copy of a VTK data object."""
    newData = dataObj.NewInstance()
    newData.DeepCopy(dataObj)
    return newData


def shallowCopy(dataObj):
    """Create a shallow copy of a VTK data object."""
    newData = dataObj.NewInstance()
    newData.ShallowCopy(dataObj)
    return newData
