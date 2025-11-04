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


class Image2DItem(om.ObjectModelItem):
    """2D image overlay item for displaying images in the viewport."""
    
    def __init__(self, name, image, view):
        """Initialize Image2DItem.
        
        Args:
            name: Name for the object model item
            image: vtkImageData instance
            view: VTKWidget view instance
        """
        om.ObjectModelItem.__init__(self, name, om.Icons.Robot)
        
        self.views = []
        self.image = image
        
        defaultWidth = 300
        defaultHeight = self._getHeightForWidth(image, defaultWidth)
        
        # Flag to prevent recursive property updates during aspect ratio sync
        self._syncing_aspect_ratio = False
        
        self.actor = vtk.vtkLogoRepresentation()
        self.actor.SetImage(image)
        self.actor.GetImageProperty().SetOpacity(1.0)
        
        actors = vtk.vtkPropCollection()
        self.actor.GetActors2D(actors)
        self.texture = actors.GetItemAsObject(0).GetTexture()
        self.actors = [actors.GetItemAsObject(i) for i in range(actors.GetNumberOfItems())]
        
        self.addProperty('Visible', True)
        self.addProperty('Anchor', 1,
                         attributes=om.PropertyAttributes(enumNames=['Top Left', 'Top Right', 'Bottom Left', 'Bottom Right']))
        self.addProperty('Width', defaultWidth,
                         attributes=om.PropertyAttributes(minimum=0, maximum=9999, singleStep=50))
        self.addProperty('Height', defaultHeight,
                         attributes=om.PropertyAttributes(minimum=0, maximum=9999, singleStep=50))
        self.addProperty('Keep Aspect Ratio', True,
                         attributes=om.PropertyAttributes(hidden=True))
        self.addProperty('Alpha', 1.0,
                         attributes=om.PropertyAttributes(decimals=2, minimum=0, maximum=1.0, singleStep=0.1))
        
        if view is not None:
            self.addToView(view)
    
    def _renderAllViews(self):
        """Render all views containing this item."""
        for view in self.views:
            view.render()
    
    def hasDataSet(self, dataSet):
        """Check if this item uses the given dataset."""
        return dataSet == self.image
    
    def hasActor(self, actor):
        """Check if this item uses the given actor."""
        return actor == self.actor
    
    def setImage(self, image):
        """Update the image displayed by this item.
        
        Args:
            image: vtkImageData instance
        """
        self.image = image
        self.actor.SetImage(image)
        
        # Also set the image on the texture, otherwise
        # the texture input won't update until the next
        # render where this actor is visible
        self.texture.SetInputData(image)
        
        if self.getProperty('Visible'):
            self._renderAllViews()
    
    def addToView(self, view):
        """Add this item to a view.
        
        Args:
            view: VTKWidget view instance
        """
        if view in self.views:
            return
        self.views.append(view)
        
        # Get renderer
        renderer = view.renderer()
        self._updatePositionCoordinates(view)
        
        renderer.AddActor(self.actor)
        view.render()
    
    def _getHeightForWidth(self, image, width):
        """Calculate height for a given width maintaining aspect ratio.
        
        Args:
            image: vtkImageData instance
            width: Desired width in pixels
            
        Returns:
            Height in pixels
        """
        dims = image.GetDimensions()
        w, h = dims[0], dims[1]
        aspect = w / float(h) if h > 0 else 1.0
        return int(np.round(width / aspect))
    
    def _getWidthForHeight(self, image, height):
        """Calculate width for a given height maintaining aspect ratio.
        
        Args:
            image: vtkImageData instance
            height: Desired height in pixels
            
        Returns:
            Width in pixels
        """
        dims = image.GetDimensions()
        w, h = dims[0], dims[1]
        aspect = w / float(h) if h > 0 else 1.0
        return int(np.round(height * aspect))
    
    def _getAspectRatio(self, image):
        """Get the aspect ratio of the image.
        
        Args:
            image: vtkImageData instance
            
        Returns:
            Aspect ratio (width/height)
        """
        dims = image.GetDimensions()
        w, h = dims[0], dims[1]
        return w / float(h) if h > 0 else 1.0
    
    def _updatePositionCoordinates(self, view):
        """Update the position coordinates for the image overlay.
        
        Args:
            view: VTKWidget view instance
        """
        width = self.getProperty('Width')
        height = self.getProperty('Height')
        
        # Get renderer
        renderer = view.renderer()
        
        pc0 = vtk.vtkCoordinate()
        pc1 = self.actor.GetPositionCoordinate()
        pc2 = self.actor.GetPosition2Coordinate()
        
        for pc in [pc0, pc1, pc2]:
            pc.SetViewport(renderer)
        
        pc0.SetReferenceCoordinate(None)
        pc0.SetCoordinateSystemToNormalizedDisplay()
        pc1.SetReferenceCoordinate(pc0)
        pc1.SetCoordinateSystemToDisplay()
        
        anchor = self.properties.getPropertyEnumValue('Anchor')
        if anchor == 'Top Left':
            pc0.SetValue(0.0, 1.0)
            pc1.SetValue(0.0, -height)
        elif anchor == 'Top Right':
            pc0.SetValue(1.0, 1.0)
            pc1.SetValue(-width, -height)
        elif anchor == 'Bottom Left':
            pc0.SetValue(0.0, 0.0)
            pc1.SetValue(0.0, 0.0)
        elif anchor == 'Bottom Right':
            pc0.SetValue(1.0, 0.0)
            pc1.SetValue(-width, 0.0)
        
        pc2.SetCoordinateSystemToDisplay()
        pc2.SetReferenceCoordinate(pc1)
        pc2.SetValue(width, height)
    
    def _onPropertyChanged(self, propertySet, propertyName):
        """Handle property changes.
        
        Args:
            propertySet: PropertySet instance
            propertyName: Name of the property that changed
        """
        om.ObjectModelItem._onPropertyChanged(self, propertySet, propertyName)
        
        # Skip aspect ratio sync if we're already syncing (prevents recursive updates)
        if self._syncing_aspect_ratio:
            if propertyName in ('Width', 'Height', 'Keep Aspect Ratio'):
                if self.views:
                    self._updatePositionCoordinates(self.views[0])
                self._renderAllViews()
            return
        
        if propertyName == 'Alpha':
            self.actor.GetImageProperty().SetOpacity(self.getProperty(propertyName))
        elif propertyName == 'Visible':
            self.actor.SetVisibility(self.getProperty(propertyName))
        elif propertyName == 'Width':
            # If keeping aspect ratio, update height
            if self.getProperty('Keep Aspect Ratio'):
                self._syncing_aspect_ratio = True
                try:
                    new_height = self._getHeightForWidth(self.image, self.getProperty('Width'))
                    self.setProperty('Height', new_height)
                finally:
                    self._syncing_aspect_ratio = False
            if self.views:
                self._updatePositionCoordinates(self.views[0])
        elif propertyName == 'Height':
            # If keeping aspect ratio, update width
            if self.getProperty('Keep Aspect Ratio'):
                self._syncing_aspect_ratio = True
                try:
                    new_width = self._getWidthForHeight(self.image, self.getProperty('Height'))
                    self.setProperty('Width', new_width)
                finally:
                    self._syncing_aspect_ratio = False
            if self.views:
                self._updatePositionCoordinates(self.views[0])
        elif propertyName == 'Anchor':
            if self.views:
                self._updatePositionCoordinates(self.views[0])
        self._renderAllViews()
    
    def onRemoveFromObjectModel(self):
        """Called when item is removed from object model."""
        om.ObjectModelItem.onRemoveFromObjectModel(self)
        self.removeFromAllViews()
    
    def removeFromAllViews(self):
        """Remove this item from all views."""
        for view in list(self.views):
            self.removeFromView(view)
        assert len(self.views) == 0
    
    def removeFromView(self, view):
        """Remove this item from a view.
        
        Args:
            view: VTKWidget view instance
        """
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
        
        if hasattr(view, 'render'):
            view.render()
        elif hasattr(view, 'vtk_widget'):
            view.vtk_widget.render()


def showImage(image, name, anchor='Top Left', parent=None, view=None):
    """Show an image in the view and optionally add it to the object model if initialized.
    
    Args:
        image: vtkImageData instance
        name: Name for the Image2DItem
        anchor: Anchor position ('Top Left', 'Top Right', 'Bottom Left', 'Bottom Right')
        parent: Parent container (string name or ObjectModelItem)
        view: VTKWidget view instance (if None, tries to get from applogic)
    
    Returns:
        Image2DItem instance
    """
    if view is None:
        # Try to get current view from applogic
        try:
            view = app.getCurrentRenderView()
        except:
            raise ValueError("view must be provided or applogic.getCurrentRenderView() must return a valid view")
    
    assert view
    
    item = Image2DItem(name, image, view)
    
    # Set anchor property - can be string or index
    if isinstance(anchor, str):
        # Find the index for the anchor string
        anchor_map = {
            'Top Left': 0,
            'Top Right': 1,
            'Bottom Left': 2,
            'Bottom Right': 3
        }
        anchor_index = anchor_map.get(anchor, 1)  # Default to 'Top Right'
        item.setProperty('Anchor', anchor_index)
    else:
        # Assume it's already an index
        item.setProperty('Anchor', anchor)
    
    # Only add to object model if it's initialized
    if om.isInitialized():
        parent_obj = getParentObj(parent)
        if parent_obj is not None:
            om.addToObjectModel(item, parent_obj)
        else:
            om.addToObjectModel(item)
    
    return item


def updatePolyData(polyData, name, **kwargs):
    obj = om.findObjectByName(name, parent=getParentObj(kwargs.get('parent')))
    if obj is None:
        obj = showPolyData(polyData, name, **kwargs)
    else:
        obj.setPolyData(polyData)
    return obj


def updateFrame(frame, name, **kwargs):
    obj = om.findObjectByName(name, parent=getParentObj(kwargs.get('parent')))
    if obj is None:
        obj = showFrame(frame, name, **kwargs)
    else:
        obj.copyFrame(frame)
    return obj

def updateImage(image, name, **kwargs):
    obj = om.findObjectByName(name, parent=getParentObj(kwargs.get('parent')))
    if obj is None:
        obj = showImage(image, name, **kwargs)
    else:
        obj.setImage(image)
    return obj


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
    if parent is None:
        return None
    elif isinstance(parent, om.ObjectModelItem):
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


def setCameraToParallelProjection(camera):
    """Switch camera to parallel (orthographic) projection mode."""
    viewAngle = np.radians(camera.GetViewAngle())
    viewDistance = np.linalg.norm(np.array(camera.GetFocalPoint()) - np.array(camera.GetPosition()))
    desiredParallelScale = np.tan(viewAngle * 0.5) * viewDistance
    camera.SetParallelScale(desiredParallelScale)
    camera.ParallelProjectionOn()


def setCameraToPerspectiveProjection(camera):
    """Switch camera to perspective projection mode."""
    parallelScale = camera.GetParallelScale()
    viewAngle = np.radians(camera.GetViewAngle())
    desiredViewDistance = parallelScale / np.tan(viewAngle * 0.5)
    focalPoint = np.array(camera.GetFocalPoint())
    viewPlaneNormal = np.array(camera.GetViewPlaneNormal())
    desiredCameraPosition = focalPoint + desiredViewDistance * viewPlaneNormal
    camera.SetPosition(desiredCameraPosition)
    camera.ParallelProjectionOff()


def enableEyeDomeLighting(view):
    """Enable eye dome lighting (EDL) shading for the view."""
    standardPass = vtk.vtkRenderStepsPass()
    edlPass = vtk.vtkEDLShading()
    edlPass.SetDelegatePass(standardPass)
    view.renderer().SetPass(edlPass)


def disableEyeDomeLighting(view):
    """Disable eye dome lighting (EDL) shading for the view."""
    view.renderer().SetPass(None)


class ViewOptionsItem(om.ObjectModelItem):
    """Object model item for controlling view options like camera projection, lighting, background, etc."""

    def __init__(self, view):
        om.ObjectModelItem.__init__(self, 'view options')

        self.view = view
        self.addProperty('Camera projection', 0, attributes=om.PropertyAttributes(enumNames=['Perspective', 'Parallel']))
        self.addProperty('View angle', view.camera().GetViewAngle(), attributes=om.PropertyAttributes(minimum=2, maximum=180))
        self.addProperty('Key light intensity', view.lightKit().GetKeyLightIntensity(), attributes=om.PropertyAttributes(minimum=0, maximum=5, singleStep=0.1, decimals=2))
        self.addProperty('Light kit', True)
        self.addProperty('Eye dome lighting', False)
        self.addProperty('Orientation widget', True)
        self.addProperty('Interactive render', True)
        self.addProperty('Gradient background', True)
        self.addProperty('Background color', view.backgroundRenderer().GetBackground())
        self.addProperty('Background color 2', view.backgroundRenderer().GetBackground2())

    def _onPropertyChanged(self, propertySet, propertyName):
        om.ObjectModelItem._onPropertyChanged(self, propertySet, propertyName)

        if propertyName in ('Gradient background', 'Background color', 'Background color 2'):
            colors = [self.getProperty('Background color'), self.getProperty('Background color 2')]

            if not self.getProperty('Gradient background'):
                colors[1] = colors[0]

            self.view.renderer().SetBackground(colors[0])
            self.view.renderer().SetBackground2(colors[1])

        elif propertyName == 'Camera projection':
            if self.getPropertyEnumValue(propertyName) == 'Perspective':
                setCameraToPerspectiveProjection(self.view.camera())
            else:
                setCameraToParallelProjection(self.view.camera())

        elif propertyName == 'Orientation widget':
            if self.getProperty(propertyName):
                self.view.orientationMarkerWidget().SetEnabled(1)
            else:
                self.view.orientationMarkerWidget().SetEnabled(0)

        elif propertyName == 'View angle':
            angle = self.getProperty(propertyName)
            self.view.camera().SetViewAngle(angle)

        elif propertyName == 'Key light intensity':
            intensity = self.getProperty(propertyName)
            self.view.lightKit().SetKeyLightIntensity(intensity)

        elif propertyName == 'Light kit':
            self.view.setLightKitEnabled(self.getProperty(propertyName))

        elif propertyName == 'Eye dome lighting':
            if self.getProperty(propertyName):
                enableEyeDomeLighting(self.view)
            else:
                disableEyeDomeLighting(self.view)

        elif propertyName == 'Interactive render':
            if self.getProperty(propertyName):
                self.view.renderWindow().GetInteractor().EnableRenderOn()
            else:
                self.view.renderWindow().GetInteractor().EnableRenderOff()

        self.view.render()

