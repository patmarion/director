"""View bounds calculation utilities."""

import numpy as np


def getVisibleActors(view):
    """Get list of visible actors in the view."""
    if view is None:
        return []
    
    renderer = view.renderer()
    if renderer is None:
        return []
    
    actors = renderer.GetActors()
    visible = []
    for i in range(actors.GetNumberOfItems()):
        actor = actors.GetItemAsObject(i)
        if actor.GetVisibility():
            visible.append(actor)
    return visible


def computeViewBoundsNoGrid(view, gridObj):
    """
    Compute view bounds excluding the grid actor.
    
    Parameters:
    -----------
    view : VTKWidget
        The view/widget
    gridObj : object
        Grid object with an actor attribute
        
    Returns:
    --------
    bounds : array
        6-element array [xmin, xmax, ymin, ymax, zmin, zmax]
    """
    if view is None or gridObj is None or not hasattr(gridObj, 'actor'):
        return np.array([-1, 1, -1, 1, -1, 1])
    
    gridObj.actor.SetUseBounds(False)
    bounds = view.renderer().ComputeVisiblePropBounds()
    gridObj.actor.SetUseBounds(True)
    return np.array(bounds)


def computeViewBoundsSoloGrid(view, gridObj):
    """
    Compute view bounds, using grid if it's the only visible actor.
    
    Parameters:
    -----------
    view : VTKWidget
        The view/widget
    gridObj : object
        Grid object with an actor attribute
        
    Returns:
    --------
    bounds : array
        6-element array [xmin, xmax, ymin, ymax, zmin, zmax]
    """
    if view is None or gridObj is None:
        return np.array([-1, 1, -1, 1, -1, 1])
    
    actors = getVisibleActors(view)
    onlyGridShowing = (len(actors) == 1) and (actors[0] == gridObj.actor)
    
    if onlyGridShowing:
        gridObj.actor.SetUseBounds(True)
        bounds = view.renderer().ComputeVisiblePropBounds()
        return np.array(bounds)
    else:
        return computeViewBoundsNoGrid(view, gridObj)

