"""View behaviors for standard interaction patterns (context menus, key bindings, etc.)."""

from qtpy import QtCore, QtGui, QtWidgets
import director.objectmodel as om
import director.visualization as vis
from director import cameracontrol
from director import propertyset
from director import frameupdater
from director.propertiespanel import PropertiesPanel
from director.vieweventfilter import ViewEventFilter


_contextMenuActions = []


def registerContextMenuActions(getActionsFunction):
    """Register a function that returns context menu actions."""
    _contextMenuActions.append(getActionsFunction)


def getContextMenuActions(view, pickedObj, pickedPoint):
    """Get all context menu actions from registered handlers."""
    actions = []
    for func in _contextMenuActions:
        actions.extend(func(view, pickedObj, pickedPoint))
    return actions


def getDefaultContextMenuActions(view, pickedObj, pickedPoint):
    """Get default context menu actions (Select, Hide, Delete)."""
    
    def onDelete():
        om.removeFromObjectModel(pickedObj)
    
    def onHide():
        pickedObj.setProperty('Visible', False)
    
    def onSelect():
        om.setActiveObject(pickedObj)
    
    actions = [
        (None, None),
        ('Select', onSelect),
        ('Hide', onHide)
    ]
    
    if pickedObj.getProperty('Deletable'):
        actions.append(('Delete', onDelete))
    
    return actions


registerContextMenuActions(getDefaultContextMenuActions)


def getShortenedName(name, maxLength=30):
    """Shorten a name to maxLength with ellipsis."""
    if len(name) > maxLength:
        name = name[:maxLength-3] + '...'
    return name


def showRightClickMenu(displayPoint, view):
    """Show right-click context menu for picked object."""
    pickedObj, pickedPoint = vis.findPickedObject(displayPoint, view)
    if not pickedObj:
        return
    
    objectName = pickedObj.getProperty('Name')
    if objectName == 'grid':
        return
    
    objectName = getShortenedName(objectName)
    
    # Convert to widget coordinates (Qt uses top-left origin)
    vtk_widget = view.vtkWidget()
    if vtk_widget:
        # displayPoint is in VTK coordinates (bottom-left origin), convert to Qt coordinates
        qtPoint = QtCore.QPoint(int(displayPoint[0]), vtk_widget.height() - int(displayPoint[1]))
        globalPos = vtk_widget.mapToGlobal(qtPoint)
    else:
        globalPos = QtCore.QPoint(int(displayPoint[0]), int(displayPoint[1]))
    
    menu = QtWidgets.QMenu(vtk_widget if vtk_widget else None)
    
    widgetAction = QtWidgets.QWidgetAction(menu)
    label = QtWidgets.QLabel('<b>%s</b>' % objectName)
    label.setContentsMargins(9, 9, 6, 6)
    widgetAction.setDefaultWidget(label)
    menu.addAction(widgetAction)
    menu.addSeparator()
    
    # Properties panel integration
    propertiesPanel = PropertiesPanel()
    propertiesPanel.connectProperties(pickedObj.properties)
    
    # Clean up when menu is hidden
    def onMenuHidden():
        propertiesPanel.clear()
    menu.aboutToHide.connect(onMenuHidden)
    
    # Create Properties submenu with the panel widget
    propertiesMenu = menu.addMenu('Properties')
    propertiesWidgetAction = QtWidgets.QWidgetAction(propertiesMenu)
    # Set a reasonable size for the panel in the menu
    propertiesPanel.setMinimumWidth(300)
    propertiesPanel.setMinimumHeight(200)
    propertiesWidgetAction.setDefaultWidget(propertiesPanel)
    propertiesMenu.addAction(propertiesWidgetAction)
    
    actions = getContextMenuActions(view, pickedObj, pickedPoint)
    
    for actionName, func in actions:
        if not actionName:
            menu.addSeparator()
        else:
            action = menu.addAction(actionName)
            action.triggered.connect(func)
    
    menu.exec_(globalPos)


def zoomToPick(displayPoint, view):
    """Zoom camera to the picked point."""
    pickedPoint, prop, _ = vis.pickProp(displayPoint, view)
    if not prop:
        return
    flyer = cameracontrol.Flyer(view)
    flyer.zoomTo(pickedPoint)
    view.flyer = flyer  # store the flyer so it doesn't get garbage collected

def getChildFrame(obj):
    """Get the child frame of an object if it exists."""
    if hasattr(obj, 'getChildFrame'):
        return obj.getChildFrame()


def toggleFrameWidget(displayPoint, view):
    """Toggle frame widget edit mode for the picked object."""
    obj, _ = vis.findPickedObject(displayPoint, view)
    
    if not isinstance(obj, vis.FrameItem):
        obj = getChildFrame(obj)
    
    if not obj:
        return False
    
    if obj.getPropertyAttribute('Edit', 'readOnly'):
        return False

    edit = not obj.getProperty('Edit')
    obj.setProperty('Edit', edit)
    
    parent = obj.parent()
    if getChildFrame(parent) == obj and not isinstance(parent, vis.GridItem):
        if edit:
            # Enabling edit widget
            current_alpha = parent.getProperty('Alpha')
            if current_alpha > 0.5:
                obj._alpha_before_toggle = current_alpha
                parent.setProperty('Alpha', 0.5)
        else:
            # Disabling edit widget
            if hasattr(obj, '_alpha_before_toggle'):
                parent.setProperty('Alpha', obj._alpha_before_toggle)
                del obj._alpha_before_toggle
    
    return True


class ViewBehaviors(ViewEventFilter):
    """Standard view behaviors (context menus, key bindings, etc.)."""
    
    CONSUMED_KEYS = ('r', 's', 'w', 'l', '3', 'p', 'f')
    
    def onLeftDoubleClick(self, event):
        """Handle left double-click to toggle frame widget."""
        displayPoint = self.getMousePositionInView(event)
        if toggleFrameWidget(displayPoint, self.view):
            return True  # Consume event
        else:
            # Call registered handlers for double-click event
            if self.callHandler(self.LEFT_DOUBLE_CLICK_EVENT, displayPoint, self.view, event):
                return True
        return False
    
    def onRightClick(self, event):
        """Handle right-click to show context menu."""
        displayPoint = self.getMousePositionInView(event)
        showRightClickMenu(displayPoint, self.view)
        return False  # Don't consume - allow default behavior
    
    def onKeyPress(self, event):
        """Handle key press events."""
        consumed = False
        
        key = str(event.text()).lower()
        
        if key == 'f':
            consumed = True
            zoomToPick(self.getCursorDisplayPosition(), self.view)
        
        elif key == 'r':
            consumed = True
            self.view.resetCamera()
            self.view.render()
        else:
            consumed = key in self.CONSUMED_KEYS
        
        return consumed
    
    def onKeyPressRepeat(self, event):
        """Handle repeated key press events."""
        consumed = frameupdater.handleKey(event)
        
        # Prevent these keys from going to vtkRenderWindow's default key press handler
        key = str(event.text()).lower()
        consumed = consumed or (key in ViewBehaviors.CONSUMED_KEYS)
        
        return consumed

