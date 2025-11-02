"""Visualization classes and utilities for displaying VTK objects in Director."""

import director.objectmodel as om
import director.applogic as app
from director.shallowCopy import shallowCopy
import director.vtkAll as vtk
from director import filterUtils
from director import transformUtils
from director import callbacks
from director.fieldcontainer import FieldContainer
from director.gridSource import makeGridPolyData
from director.viewbounds import computeViewBoundsNoGrid, computeViewBoundsSoloGrid
import numpy as np
import colorsys


class PolyDataItem(om.ObjectModelItem):

    defaultScalarRangeMap = {
        # 'intensity' : (400, 4000),
        'spindle_angle' : (0, 360),
        'azimuth' : (-2.5, 2.5),
        'scan_delta' : (0.0, 0.3),
        'point distance to plane' : (-0.2, 0.2),
        'normal angle to plane' : (0.0, 10.0),
        }

    def __init__(self, name, polyData, view):

        om.ObjectModelItem.__init__(self, name, om.Icons.Robot)

        self.views = []
        self.polyData = polyData
        self.mapper = vtk.vtkPolyDataMapper()
        self.mapper.SetInputData(self.polyData)
        self.actor = vtk.vtkActor()
        self.actor.SetMapper(self.mapper)
        self.shadowActor = None
        self.scalarBarWidget = None
        self.extraViewRenderers = {}

        self.rangeMap = dict(PolyDataItem.defaultScalarRangeMap)

        self.addProperty('Color By', 0, attributes=om.PropertyAttributes(enumNames=['Solid Color']))
        self.addProperty('Visible', True)
        self.addProperty('Alpha', 1.0,
                         attributes=om.PropertyAttributes(decimals=2, minimum=0, maximum=1.0, singleStep=0.1, hidden=False))
        self.addProperty('Point Size', self.actor.GetProperty().GetPointSize(),
                         attributes=om.PropertyAttributes(decimals=0, minimum=1, maximum=20, singleStep=1, hidden=False))
        self.addProperty('Line Width', self.actor.GetProperty().GetLineWidth(),
                         attributes=om.PropertyAttributes(decimals=0, minimum=1, maximum=20, singleStep=1, hidden=False))
        self.addProperty('Surface Mode', 0,
                         attributes=om.PropertyAttributes(enumNames=['Surface', 'Wireframe', 'Surface with edges', 'Points'], hidden=True))
        self.addProperty('Color', [1.0, 1.0, 1.0])
        self.addProperty('Show Scalar Bar', False)

        self._updateSurfaceProperty()
        self._updateColorByProperty()

        if view is not None:
            self.addToView(view)

    def _renderAllViews(self):
        for view in self.views:
            if hasattr(view, 'render'):
                view.render()
            elif hasattr(view, 'vtk_widget'):
                view.vtk_widget.render()

    def hasDataSet(self, dataSet):
        return dataSet == self.polyData

    def hasActor(self, actor):
        return actor == self.actor

    def setPolyData(self, polyData):
        self.polyData = polyData
        self.mapper.SetInputData(polyData)

        self._updateSurfaceProperty()
        self._updateColorByProperty()
        self._updateColorBy(retainColorMap=True)

        if self.getProperty('Visible'):
            self._renderAllViews()

    def setRangeMap(self, key, value):
        self.rangeMap[key] = value

    def getArrayNames(self):
        pointData = self.polyData.GetPointData()
        return [pointData.GetArrayName(i) for i in range(pointData.GetNumberOfArrays())]

    def setSolidColor(self, color):
        self.setProperty('Color', [float(c) for c in color])
        self.colorBy(None)

    def _isPointCloud(self):
        return self.polyData.GetNumberOfPoints() and (self.polyData.GetNumberOfCells() == self.polyData.GetNumberOfVerts())

    def colorBy(self, arrayName, scalarRange=None, lut=None):
        if not arrayName:
            self.mapper.ScalarVisibilityOff()
            self.polyData.GetPointData().SetActiveScalars(None)
            return

        array = self.polyData.GetPointData().GetArray(arrayName)
        if not array:
            print('colorBy(%s): array not found' % arrayName)
            self.mapper.ScalarVisibilityOff()
            self.polyData.GetPointData().SetActiveScalars(None)
            return

        self.polyData.GetPointData().SetActiveScalars(arrayName)

        if not lut:
            lut = self._getDefaultColorMap(array, scalarRange)

        self.mapper.ScalarVisibilityOn()
        self.mapper.SetUseLookupTableScalarRange(True)
        self.mapper.SetLookupTable(lut)
        self.mapper.SetInterpolateScalarsBeforeMapping(not self._isPointCloud())

        if self.getProperty('Visible'):
            self._renderAllViews()

    def getChildFrame(self):
        frameName = self.getProperty('Name') + ' frame'
        return self.findChild(frameName)

    def addToView(self, view):
        if view in self.views:
            return

        self.views.append(view)
        
        # Get renderer - handle both VTKWidget and views with renderer() method
        if hasattr(view, 'renderer'):
            renderer = view.renderer()
        elif hasattr(view, 'vtk_widget') and hasattr(view.vtk_widget, 'renderer'):
            renderer = view.vtk_widget.renderer()
        else:
            raise ValueError("View does not have a renderer accessible via renderer() or vtk_widget.renderer()")
        
        renderer.AddActor(self.actor)
        if self.shadowActor:
            renderer.AddActor(self.shadowActor)
        
        if hasattr(view, 'render'):
            view.render()
        elif hasattr(view, 'vtk_widget'):
            view.vtk_widget.render()

    def _onPropertyChanged(self, propertySet, propertyName):
        om.ObjectModelItem._onPropertyChanged(self, propertySet, propertyName)

        if propertyName == 'Point Size':
            self.actor.GetProperty().SetPointSize(self.getProperty(propertyName))
        elif propertyName == 'Line Width':
            self.actor.GetProperty().SetLineWidth(self.getProperty(propertyName))
        elif propertyName == 'Alpha':
            self.actor.GetProperty().SetOpacity(self.getProperty(propertyName))
            if self.shadowActor:
                self.shadowActor.GetProperty().SetOpacity(self.getProperty(propertyName))
        elif propertyName == 'Visible':
            self.actor.SetVisibility(self.getProperty(propertyName))
            if self.shadowActor:
                self.shadowActor.SetVisibility(self.getProperty(propertyName))
        elif propertyName == 'Surface Mode':
            mode = self.properties.getPropertyEnumValue(propertyName)
            prop = self.actor.GetProperty()
            if mode == 'Surface':
                prop.SetRepresentationToSurface()
                prop.EdgeVisibilityOff()
            if mode == 'Wireframe':
                prop.SetRepresentationToWireframe()
            elif mode == 'Surface with edges':
                prop.SetRepresentationToSurface()
                prop.EdgeVisibilityOn()
            elif mode == 'Points':
                prop.SetRepresentationToPoints()
        elif propertyName == 'Color':
            color = self.getProperty(propertyName)
            self.actor.GetProperty().SetColor(color)
        elif propertyName == 'Color By':
            self._updateColorBy()
        elif propertyName == 'Show Scalar Bar':
            self._updateScalarBar()

        self._renderAllViews()

    def setScalarRange(self, rangeMin, rangeMax):
        arrayName = self.properties.getPropertyEnumValue('Color By')
        if arrayName != 'Solid Color':
            lut = self.mapper.GetLookupTable()
            self.colorBy(arrayName, scalarRange=(rangeMin, rangeMax))

    def _updateSurfaceProperty(self):
        hasPolys = self.polyData.GetNumberOfPolys() or self.polyData.GetNumberOfStrips()
        hasLines = self.polyData.GetNumberOfLines()

        enableSurfaceMode = hasPolys or hasLines
        self.properties.setPropertyAttribute('Surface Mode', 'hidden', not enableSurfaceMode)

        enableLineWidth = enableSurfaceMode
        self.properties.setPropertyAttribute('Line Width', 'hidden', not enableLineWidth)

        enablePointSize = True
        self.properties.setPropertyAttribute('Point Size', 'hidden', not enablePointSize)

    def _updateColorBy(self, retainColorMap=False):
        arrayName = self.properties.getPropertyEnumValue('Color By')
        if arrayName == 'Solid Color':
            self.colorBy(None)
        else:
            lut = self.mapper.GetLookupTable() if retainColorMap else None
            self.colorBy(arrayName, lut=lut)

        self._updateScalarBar()

    def _updateColorByProperty(self):
        enumNames = ['Solid Color'] + self.getArrayNames()
        currentValue = self.properties.getProperty('Color By')
        if currentValue >= len(enumNames):
            self.setProperty('Color By', 0)
        self.properties.setPropertyAttribute('Color By', 'enumNames', enumNames)

    def _updateScalarBar(self):
        # Scalar bar implementation can be added later if needed
        pass

    def _getDefaultColorMap(self, array, scalarRange=None, hueRange=None):
        name = array.GetName() if array.GetName() else ''

        blueToRed = (0.667, 0)
        redtoBlue = (0, 0.667)

        hueMap = {
            'Axes' : redtoBlue
        }

        scalarRange = scalarRange or self.rangeMap.get(name, array.GetRange())
        hueRange = hueRange or hueMap.get(name, blueToRed)

        lut = vtk.vtkLookupTable()
        lut.SetNumberOfColors(256)
        lut.SetHueRange(hueRange)
        lut.SetRange(scalarRange)
        lut.Build()

        return lut

    def onRemoveFromObjectModel(self):
        om.ObjectModelItem.onRemoveFromObjectModel(self)
        self.removeFromAllViews()

    def removeFromAllViews(self):
        for view in list(self.views):
            self.removeFromView(view)
        assert len(self.views) == 0

    def removeFromView(self, view):
        assert view in self.views
        self.views.remove(view)
        
        # Get renderer
        if hasattr(view, 'renderer'):
            renderer = view.renderer()
        elif hasattr(view, 'vtk_widget') and hasattr(view.vtk_widget, 'renderer'):
            renderer = view.vtk_widget.renderer()
        else:
            return
        
        renderer.RemoveActor(self.actor)
        if self.shadowActor:
            renderer.RemoveActor(self.shadowActor)
        
        if hasattr(view, 'render'):
            view.render()
        elif hasattr(view, 'vtk_widget'):
            view.vtk_widget.render()


def createAxesPolyData(scale, useTube, tubeWidth=0.002):
    axes = vtk.vtkAxes()
    axes.SetComputeNormals(0)
    axes.SetScaleFactor(scale)
    axes.Update()

    if useTube:
        tube = vtk.vtkTubeFilter()
        tube.SetInputConnection(axes.GetOutputPort())
        tube.SetRadius(tubeWidth)
        tube.SetNumberOfSides(12)
        tube.Update()
        axes = tube

    return shallowCopy(axes.GetOutput())


class FrameItem(PolyDataItem):
    """FrameItem with interactive frame widget support."""

    def __init__(self, name, transform, view):
        PolyDataItem.__init__(self, name, vtk.vtkPolyData(), view)

        self.transform = transform
        self._blockSignals = False
        self.frameWidget = None

        self.actor.SetUserTransform(transform)

        self.addProperty('Scale', 1.0, attributes=om.PropertyAttributes(decimals=2, minimum=0.01, maximum=100, singleStep=0.1, hidden=False))
        self.addProperty('Edit', False)
        self.addProperty('Tube', False)
        self.addProperty('Tube Width', 0.002, attributes=om.PropertyAttributes(decimals=3, minimum=0.001, maximum=10, singleStep=0.01, hidden=True))
        
        # Set Edit as the first property
        self.properties.setPropertyIndex('Edit', 0)

        # Initialize callbacks with FrameModified signal
        self.callbacks = callbacks.CallbackRegistry(['FrameModified'])
        self.onTransformModifiedCallback = None
        self.observerTag = self.transform.AddObserver('ModifiedEvent', self.onTransformModified)
        self._updateAxesGeometry()

        self.setProperty('Color By', 'Axes')
        self.setProperty('Icon', om.Icons.Axes)
        self._updateFrameWidget()

    def connectFrameModified(self, func):
        return self.callbacks.connect('FrameModified', func)

    def disconnectFrameModified(self, callbackId):
        self.callbacks.disconnect(callbackId)

    def onTransformModified(self, transform, event):
        if not self._blockSignals:
            if self.onTransformModifiedCallback:
                self.onTransformModifiedCallback(self)
            self.callbacks.process('FrameModified', self)

    def copyFrame(self, transform):
        self._blockSignals = True
        self.transform.SetMatrix(transform.GetMatrix())
        self._blockSignals = False
        self.transform.Modified()
        parent = self.parent()
        if (parent and parent.getProperty('Visible')) or self.getProperty('Visible'):
            self._renderAllViews()

    def _updateAxesGeometry(self):
        scale = self.getProperty('Scale')
        self.setPolyData(createAxesPolyData(scale, self.getProperty('Tube'), self.getProperty('Tube Width')))
        # Update frame widget scale if it exists
        if self.frameWidget:
            self.frameWidget.setScale(scale)
    
    def _onPropertyChanged(self, propertySet, propertyName):
        """Handle property changes."""
        PolyDataItem._onPropertyChanged(self, propertySet, propertyName)
        
        if propertyName == 'Edit':
            print("Edit changed:", self.properties.edit)
            self._updateFrameWidget()

        elif propertyName == 'Visible':
            pass
        elif propertyName == 'Scale':
            self._updateAxesGeometry()
        elif propertyName == 'Tube':
            self.properties.setPropertyAttribute('Tube Width', 'hidden', not self.getProperty(propertyName))
            self._updateAxesGeometry()
    
    def _updateFrameWidget(self):
        """Create or destroy frame widget based on Edit property."""
        if not self.hasProperty('Edit'):
            return
        edit = self.getProperty('Edit')
        
        # Get the view (prefer current view, otherwise first view)
        try:
            view = self.views[0]
        except IndexError:
            return
        
        if edit:
            if self.frameWidget is None:
                # Create frame widget
                from director.framewidget import FrameWidget
                scale = self.getProperty('Scale')
                # Set callback to trigger FrameModified signal when transform changes
                self.frameWidget = FrameWidget(view, self.transform, scale=scale, 
                                               onTransformModified=self.onTransformModified)
            # Ensure widget is enabled and visible (regardless of whether it was just created)
            self.frameWidget.setEnabled(True)
            self.frameWidget.view.render()
        else:
            if self.frameWidget:
                # Disable widget but don't destroy it (keep it for toggling)
                self.frameWidget.setEnabled(False)
                self.frameWidget.view.render()
    
    def addToView(self, view):
        """Add frame item to a view."""
        PolyDataItem.addToView(self, view)
        self._updateFrameWidget()
    
    def removeFromView(self, view):
        """Remove frame item from a view."""
        # Clean up frame widget if it exists
        if self.frameWidget:
            self.frameWidget.cleanup()
            self.frameWidget = None
        PolyDataItem.removeFromView(self, view)

    def onRemoveFromObjectModel(self):
        PolyDataItem.onRemoveFromObjectModel(self)
        self.transform.RemoveObserver(self.observerTag)


def getParentObj(parent):
    """Get parent object from name or object."""
    if isinstance(parent, om.ObjectModelItem):
        return parent
    elif isinstance(parent, str):
        return om.getOrCreateContainer(parent)
    raise ValueError("Invalid parent: %s" % parent)


def showPolyData(polyData, name, color=None, colorByName=None, colorByRange=None, alpha=1.0, visible=True, view=None, parent='data', cls=None):
    """Show polyData in the view and optionally add it to the object model if initialized."""
    if view is None:
        # Try to get current view from applogic
        try:
            view = app.getCurrentRenderView()
        except:
            raise ValueError("view must be provided or applogic.getCurrentRenderView() must return a valid view")
    
    assert view

    cls = cls or PolyDataItem
    item = cls(name, polyData, view)

    # Only add to object model if it's initialized
    if om.isInitialized():
        om.addToObjectModel(item, getParentObj(parent))
    
    item.setProperty('Visible', visible)
    item.setProperty('Alpha', alpha)

    if colorByName and colorByName not in item.getArrayNames():
        print('showPolyData(colorByName=%s): array not found' % colorByName)
        colorByName = None

    if colorByName:
        item.setProperty('Color By', colorByName)
        item.colorBy(colorByName, colorByRange)
    else:
        color = [1.0, 1.0, 1.0] if color is None else color
        item.setProperty('Color', [float(c) for c in color])
        item.colorBy(None)

    return item


def addChildFrame(obj, initialTransform=None):
    '''
    Adds a child frame to the given PolyDataItem.  If initialTransform is given,
    the object's polydata is transformed using the inverse of initialTransform
    and then a child frame is assigned to the object to maintain its original
    position.
    '''
    if obj.getChildFrame():
        return obj.getChildFrame()

    if initialTransform:
        pd = filterUtils.transformPolyData(obj.polyData, initialTransform.GetLinearInverse())
        obj.setPolyData(pd)
        t = initialTransform
    else:
        t = obj.actor.GetUserTransform()

    if t is None:
        t = vtk.vtkTransform()
        t.PostMultiply()

    # Use the first view from the object's views
    view = obj.views[0] if obj.views else None
    frame = showFrame(t, obj.getProperty('Name') + ' frame', parent=obj, scale=0.2, visible=False, view=view)
    for view in obj.views:
        frame.addToView(view)
    obj.actor.SetUserTransform(t)

    return frame


def showFrame(frame, name, view=None, parent='data', scale=0.35, visible=True, alpha=1.0):
    """Show a coordinate frame (vtkTransform) in the view."""
    if view is None:
        try:
            view = app.getCurrentRenderView()
        except:
            raise ValueError("view must be provided or applogic.getCurrentRenderView() must return a valid view")
    
    assert view

    item = FrameItem(name, frame, view)
    om.addToObjectModel(item, getParentObj(parent))
    item.setProperty('Visible', visible)
    item.setProperty('Alpha', alpha)
    item.setProperty('Scale', scale)
    return item


def pickProp(displayPoint, view):
    """Pick a prop at the given display point."""
    for tolerance in (0.0, 0.005, 0.01):
        pickType = 'render' if tolerance == 0.0 else 'cells'
        pickData = pickPoint(displayPoint, view, pickType=pickType, tolerance=tolerance)
        pickedPoint = pickData.pickedPoint
        pickedProp = pickData.pickedProp
        pickedDataset = pickData.pickedDataset
        if pickedProp is not None:
            return pickedPoint, pickedProp, pickedDataset
    
    return None, None, None


def pickPoint(displayPoint, view, obj=None, pickType='points', tolerance=0.01):
    """
    Pick a point/object at the given display point.
    
    :param displayPoint: (x, y) tuple in display coordinates
    :param view: VTKWidget view
    :param obj: Optional object to limit picking to
    :param pickType: 'points', 'cells', or 'render'
    :param tolerance: Picking tolerance
    :return: FieldContainer with fields:
        pickedPoint: numpy array of picked point in world coordinates
        pickedProp: vtkProp that was picked
        pickedDataset: vtkDataSet that was picked
        pickedNormal: normal vector (None if not available)
        pickedCellId: cell ID (None unless pickType="cells")
    """
    assert pickType in ('points', 'cells', 'render')
    
    view = view or app.getCurrentRenderView()
    assert view
    
    if isinstance(obj, str):
        obj = om.findObjectByName(obj)
        assert obj
    
    wasTexturedBackground = False
    if pickType == 'render':
        picker = vtk.vtkPropPicker()
        wasTexturedBackground = view.renderer().GetTexturedBackground()
        view.renderer().TexturedBackgroundOff()
    else:
        picker = vtk.vtkPointPicker() if pickType == 'points' else vtk.vtkCellPicker()
        picker.SetTolerance(tolerance)
    
    if obj is not None:
        if isinstance(obj, list):
            for o in obj:
                picker.AddPickList(o.actor)
            obj = None
        else:
            picker.AddPickList(obj.actor)
        picker.PickFromListOn()
    
    picker.Pick(displayPoint[0], displayPoint[1], 0, view.renderer())
    if wasTexturedBackground:
        view.renderer().TexturedBackgroundOn()
    
    pickedProp = picker.GetViewProp()
    pickedPoint = np.array(picker.GetPickPosition())
    pickedDataset = pickedProp.GetMapper().GetInput() if isinstance(pickedProp, vtk.vtkActor) and pickedProp.GetMapper() else None
    
    if pickType == "cells":
        pickedCellId = picker.GetCellId()
    else:
        pickedCellId = None
    
    # Populate pickedNormal if possible
    pickedNormal = None
    if pickType == 'cells' and pickedProp:
        try:
            pickedNormal = np.array(picker.GetPickNormal())
        except:
            pass
    elif pickType == 'points' and pickedDataset:
        pointId = picker.GetPointId()
        if pointId >= 0:
            normals = pickedDataset.GetPointData().GetNormals()
            if normals:
                pickedNormal = np.array(normals.GetTuple3(pointId))
    
    fields = FieldContainer(
        pickedPoint=pickedPoint,
        pickedProp=pickedProp,
        pickedDataset=pickedDataset,
        pickedNormal=pickedNormal,
        pickedCellId=pickedCellId
    )
    return fields


def getObjectByDataSet(dataSet):
    """Find an object that has the given dataset."""
    if not dataSet:
        return None
    for obj in om.getObjects():
        if obj.hasDataSet(dataSet):
            return obj
    return None


def getObjectByProp(prop):
    """Find an object that has the given prop (actor)."""
    if not prop:
        return None
    for obj in om.getObjects():
        if obj.hasActor(prop):
            return obj
    return None


def findPickedObject(displayPoint, view):
    """Find the picked object at the given display point."""
    pickedPoint, pickedProp, pickedDataset = pickProp(displayPoint, view)
    obj = getObjectByProp(pickedProp) or getObjectByDataSet(pickedDataset)
    return obj, pickedPoint


class GridItem(PolyDataItem):
    """Grid item for displaying a reference grid in the 3D view."""
    
    def __init__(self, name, view=None):
        PolyDataItem.__init__(self, name, polyData=vtk.vtkPolyData(), view=view)
        self.actor.PickableOff()  # Grid shouldn't be pickable
        self.actor.GetProperty().LightingOff()  # No lighting for grid
        self.textActors = []  # Text actors for grid labels (simplified for now)
        
        # Grid properties
        self.addProperty('Grid Half Width', 10.0, 
                       attributes=om.PropertyAttributes(minimum=0.01, maximum=1e6, singleStep=1, decimals=2))
        self.addProperty('Major Tick Resolution', 10, 
                       attributes=om.PropertyAttributes(minimum=1, maximum=100, singleStep=1))
        self.addProperty('Minor Tick Resolution', 2, 
                       attributes=om.PropertyAttributes(minimum=1, maximum=100, singleStep=1))
        self.addProperty('Major Tick Rings', True)
        self.addProperty('Minor Tick Rings', False)
        
        self._updateGrid()
        self.setProperty('Surface Mode', 'Wireframe')
        self.setProperty('Color', [0.5, 0.5, 0.5])  # Gray grid
    
    def _onPropertyChanged(self, propertySet, propertyName):
        PolyDataItem._onPropertyChanged(self, propertySet, propertyName)
        if propertyName in ('Grid Half Width', 'Major Tick Resolution',
                            'Minor Tick Resolution', 'Major Tick Rings', 'Minor Tick Rings'):
            self._updateGrid()
    
    def _updateGrid(self):
        """Update the grid geometry based on current properties."""
        gridHalfWidth = self.getProperty('Grid Half Width')
        majorTickSize = gridHalfWidth / self.getProperty('Major Tick Resolution')
        minorTickSize = majorTickSize / self.getProperty('Minor Tick Resolution')
        majorTickRings = self.getProperty('Major Tick Rings')
        minorTickRings = self.getProperty('Minor Tick Rings')
        
        polyData = makeGridPolyData(gridHalfWidth, majorTickSize, minorTickSize,
                                   majorTickRings, minorTickRings)
        self.setPolyData(polyData)


def showGrid(view, cellSize=0.5, numberOfCells=25, name='grid', parent='scene', 
             color=[0.5, 0.5, 0.5], alpha=0.3, gridTransform=None):
    """Show a grid in the view and add it to the object model."""
    if view is None:
        try:
            view = app.getCurrentRenderView()
        except:
            raise ValueError("view must be provided or applogic.getCurrentRenderView() must return a valid view")
    
    assert view
    
    gridObj = GridItem(name, view=view)
    
    gridHalfWidth = cellSize * numberOfCells
    gridObj.setProperty('Grid Half Width', gridHalfWidth)
    gridObj.setProperty('Major Tick Resolution', numberOfCells)
    gridObj.setProperty('Minor Tick Resolution', 2)
    gridObj.setProperty('Major Tick Rings', False)
    gridObj.setProperty('Minor Tick Rings', False)
    gridObj.setProperty('Alpha', alpha)
    gridObj.setProperty('Color', color)
    
    # Set up view bounds function to exclude grid from bounds calculations
    gridObj.viewBoundsFunction = computeViewBoundsNoGrid
    gridObj.emptyBoundsSize = 1.0
    
    om.addToObjectModel(gridObj, parentObj=getParentObj(parent))
    
    # Add child frame if requested
    if gridTransform:
        frame = addChildFrame(gridObj)
        frame.copyFrame(gridTransform)
    
    return gridObj

