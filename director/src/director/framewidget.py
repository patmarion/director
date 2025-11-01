"""Frame widget for manipulating an orthonormal frame in 3D view."""

import numpy as np
import director.vtkAll as vtk
from director.vieweventfilter import ViewEventFilter
from director.shallowCopy import shallowCopy
from director.transformUtils import getAxesFromTransform, getTransformFromAxesAndOrigin
from qtpy.QtCore import Qt

try:
    from vtk import mutable
except ImportError:
    # Fallback for older VTK versions
    class mutable:
        def __init__(self, value):
            self._value = value
        def get(self):
            return self._value
        def set(self, value):
            self._value = value


def createAxisGeometry(scale, radius, axisId, useTubeFilter=True):
    """
    Create geometry for a frame axis (line/tube with sphere tip).
    
    Parameters:
    -----------
    scale : float
        Base scale - axis extends to scale * 1.5
    radius : float
        Radius of the tube
    axisId : int
        0=X (red), 1=Y (green), 2=Z (blue)
    useTubeFilter : bool
        Whether to use tube filter for smooth cylinders
        
    Returns:
    --------
    polyData : vtkPolyData
        The axis geometry
    """
    # Axis extends from origin to scale * 1.5 (like C++ version)
    axisLength = scale * 1.5
    
    # Create line for the shaft
    line = vtk.vtkLineSource()
    line.SetPoint1(0, 0, 0)
    line.SetPoint2(axisLength, 0, 0)
    line.Update()
    
    # Create sphere for the tip
    sphere = vtk.vtkSphereSource()
    sphere.SetCenter(axisLength, 0, 0)
    sphere.SetRadius(0.057 * scale)  # Match C++ implementation
    sphere.SetThetaResolution(32)
    sphere.SetPhiResolution(32)
    sphere.Update()
    
    # Append line and sphere
    append = vtk.vtkAppendPolyData()
    append.AddInputData(shallowCopy(line.GetOutput()))
    append.AddInputData(shallowCopy(sphere.GetOutput()))
    append.Update()
    
    if useTubeFilter:
        # Apply tube filter to the line part
        # We need to separate line and sphere for this
        lineTube = vtk.vtkTubeFilter()
        lineTube.SetInputConnection(line.GetOutputPort())
        lineTube.SetRadius(radius)
        lineTube.SetNumberOfSides(24)
        lineTube.Update()
        
        # Append tube and sphere
        append = vtk.vtkAppendPolyData()
        append.AddInputData(shallowCopy(lineTube.GetOutput()))
        append.AddInputData(shallowCopy(sphere.GetOutput()))
        append.Update()
        polyData = shallowCopy(append.GetOutput())
    else:
        polyData = shallowCopy(append.GetOutput())
    
    # Transform to align with correct axis
    # X axis (axisId=0): no transform needed (already along X)
    # Y axis (axisId=1): rotate 90 degrees around Z
    # Z axis (axisId=2): rotate -90 degrees around Y
    if axisId == 1 or axisId == 2:
        transform = vtk.vtkTransform()
        if axisId == 1:  # Y axis
            transform.RotateZ(90)
        elif axisId == 2:  # Z axis
            transform.RotateY(-90)
        
        transformFilter = vtk.vtkTransformPolyDataFilter()
        transformFilter.SetTransform(transform)
        transformFilter.SetInputData(polyData)
        transformFilter.Update()
        return shallowCopy(transformFilter.GetOutput())
    else:
        return polyData


def createRingGeometry(scale, radius, axisId, useTubeFilter=True):
    """
    Create geometry for a ring on a plane orthogonal to an axis.
    
    Parameters:
    -----------
    scale : float
        Radius of the ring
    radius : float
        Tube radius for the ring
    axisId : int
        0=YZ plane (orthogonal to X axis, red ring)
        1=XZ plane (orthogonal to Y axis, green ring)
        2=XY plane (orthogonal to Z axis, blue ring)
    useTubeFilter : bool
        Whether to create a tube ring (True) or flat disk (False)
        
    Returns:
    --------
    polyData : vtkPolyData
        The ring geometry
    """
    if useTubeFilter:
        # Create a regular polygon as a circle
        circle = vtk.vtkRegularPolygonSource()
        circle.SetNumberOfSides(64)
        circle.SetRadius(scale)
        circle.SetCenter(0, 0, 0)
        circle.GeneratePolygonOn()
        circle.Update()
        
        # Transform to correct plane
        # Ring is created in XY plane, need to rotate to be orthogonal to the axis
        # Matching C++ implementation: axis 0=RotateY(-90), axis 1=RotateX(90), axis 2=no rotation
        ringTransform = vtk.vtkTransform()
        if axisId == 0:  # YZ plane (orthogonal to X axis, red ring)
            ringTransform.RotateY(-90)  # Rotate around Y (negative) to put circle in YZ plane
        elif axisId == 1:  # XZ plane (orthogonal to Y axis, green ring)
            ringTransform.RotateX(90)  # Rotate around X to put circle in XZ plane
        elif axisId == 2:  # XY plane (orthogonal to Z axis, blue ring)
            pass  # Already in XY plane, no rotation needed
        
        transformFilter = vtk.vtkTransformPolyDataFilter()
        transformFilter.SetTransform(ringTransform)
        transformFilter.SetInputConnection(circle.GetOutputPort())
        transformFilter.Update()
        
        # Apply tube filter
        tube = vtk.vtkTubeFilter()
        tube.SetInputConnection(transformFilter.GetOutputPort())
        tube.SetRadius(radius)
        tube.SetNumberOfSides(16)
        tube.CappingOn()
        tube.Update()
        
        return shallowCopy(tube.GetOutput())
    else:
        # Create a flat disk
        disk = vtk.vtkDiskSource()
        disk.SetInnerRadius(scale * 0.9)
        disk.SetOuterRadius(scale)
        disk.SetRadialResolution(1)
        disk.SetCircumferentialResolution(64)
        disk.Update()
        
        # Transform to correct plane
        diskTransform = vtk.vtkTransform()
        if axisId == 0:  # YZ plane (orthogonal to X axis)
            diskTransform.RotateY(-90)  # Match C++: RotateY(-90)
        elif axisId == 1:  # XZ plane (orthogonal to Y axis)
            diskTransform.RotateX(90)
        elif axisId == 2:  # XY plane (orthogonal to Z axis)
            pass  # Already in XY plane
        
        transformFilter = vtk.vtkTransformPolyDataFilter()
        transformFilter.SetTransform(diskTransform)
        transformFilter.SetInputConnection(disk.GetOutputPort())
        transformFilter.Update()
        
        return shallowCopy(transformFilter.GetOutput())


class FrameWidget(ViewEventFilter):
    """
    Interactive frame widget for manipulating a vtkTransform.
    
    Features:
    - Axes: Left click + drag to translate along axis, right click + drag to rotate about axis
    - Rings: Left click + drag to translate in plane, right click + drag to rotate about plane normal
    """
    
    # Interaction states
    OUTSIDE = 0
    TRANSLATING = 1
    TRANSLATING_IN_PLANE = 2
    ROTATING = 3
    
    def __init__(self, view, transform, scale=0.5, useTubeFilter=True, useDiskRings=False):
        """
        Initialize the frame widget.
        
        Parameters:
        -----------
        view : VTKWidget
            The view widget to display in
        transform : vtkTransform
            The transform to manipulate (will be modified in place)
        scale : float
            Size of the frame axes and rings
        useTubeFilter : bool
            Whether to use tube filter for smooth appearance
        useDiskRings : bool
            Whether to draw rings as flat disks (True) or tubes (False)
        """
        super().__init__(view)
        self.transform = transform
        self.scale = scale
        self.useTubeFilter = useTubeFilter
        self.useDiskRings = useDiskRings
        
        # Interaction state
        self.interactionState = self.OUTSIDE
        self.interactingAxis = -1
        self.lastEventPosition = [0.0, 0.0]
        self.startWorldPoint = np.array([0.0, 0.0, 0.0])
        self.startEventPosition = [0.0, 0.0]
        
        # Create geometry
        self.axisActors = []
        self.ringActors = []
        self.axisPolys = []
        self.ringPolys = []
        self._buildActors()
        
        # Setup picker
        self.picker = vtk.vtkCellPicker()
        self.picker.SetTolerance(0.005)
        self.picker.PickFromListOn()
        for actor in self.axisActors + self.ringActors:
            self.picker.AddPickList(actor)
        
        # Add actors to renderer (axes first so they render behind rings if needed)
        renderer = view.renderer()
        for actor in self.axisActors:
            renderer.AddActor(actor)
        for actor in self.ringActors:
            renderer.AddActor(actor)
        
        # Highlight state
        self.highlightedActor = None
        
    def _buildActors(self):
        """Build the actors for axes and rings."""
        handleRadius = 0.015 * self.scale
        
        # Create axes (cylinders with cone tips)
        axisColors = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]  # R, G, B
        
        for axisId in range(3):
            polyData = createAxisGeometry(self.scale, handleRadius, axisId, self.useTubeFilter)
            self.axisPolys.append(polyData)
            
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputData(polyData)
            
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(axisColors[axisId])
            actor.SetUserTransform(self.transform)
            
            self.axisActors.append(actor)
        
        # Create rings (orthogonal to axes)
        # Ring 0 = YZ plane (orthogonal to X axis, red ring)
        # Ring 1 = XZ plane (orthogonal to Y axis, green ring)
        # Ring 2 = XY plane (orthogonal to Z axis, blue ring)
        ringColors = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]  # Red, Green, Blue matching axes
        
        for ringId in range(3):
            polyData = createRingGeometry(self.scale, handleRadius, ringId, 
                                          useTubeFilter=not self.useDiskRings)
            self.ringPolys.append(polyData)
            
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputData(polyData)
            
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(ringColors[ringId])
            actor.GetProperty().SetOpacity(0.8)  # More visible
            actor.SetUserTransform(self.transform)
            
            self.ringActors.append(actor)
    
    def _pickActor(self, x, y):
        """Pick an actor at screen coordinates."""
        renderer = self.view.renderer()
        self.picker.Pick(x, y, 0, renderer)
        
        pickedProp = self.picker.GetViewProp()
        if pickedProp is None:
            return None, -1
        
        # Check if it's an axis or ring
        for i, actor in enumerate(self.axisActors):
            if pickedProp == actor:
                return 'axis', i
        
        for i, actor in enumerate(self.ringActors):
            if pickedProp == actor:
                return 'ring', i
        
        return None, -1
    
    def _brightenColor(self, color):
        """Brighten a color by adding brightness and clamping to [0,1]."""
        brightness = 0.3
        return [min(1.0, c + brightness) for c in color]
    
    def _updateHighlight(self, pickedType, pickedId):
        """Update highlight on hover - brightens original colors."""
        # Remove previous highlight - restore original color
        if self.highlightedActor:
            prop = self.highlightedActor.GetProperty()
            if hasattr(prop, '_originalColor'):
                prop.SetColor(prop._originalColor)
            self.highlightedActor = None
        
        # Set new highlight - brighten original color
        if pickedType == 'axis' and 0 <= pickedId < len(self.axisActors):
            actor = self.axisActors[pickedId]
            prop = actor.GetProperty()
            if not hasattr(prop, '_originalColor'):
                prop._originalColor = list(prop.GetColor())
            # Brighten the original color
            brightColor = self._brightenColor(prop._originalColor)
            prop.SetColor(brightColor)
            self.highlightedActor = actor
        elif pickedType == 'ring' and 0 <= pickedId < len(self.ringActors):
            actor = self.ringActors[pickedId]
            prop = actor.GetProperty()
            if not hasattr(prop, '_originalColor'):
                prop._originalColor = list(prop.GetColor())
            # Brighten the original color
            brightColor = self._brightenColor(prop._originalColor)
            prop.SetColor(brightColor)
            self.highlightedActor = actor
    
    def _getWorldRay(self, x, y):
        """Get world ray from screen coordinates."""
        renderer = self.view.renderer()
        
        # Convert screen to world using vtkInteractorObserver
        worldPt1 = [0.0, 0.0, 0.0, 0.0]
        worldPt2 = [0.0, 0.0, 0.0, 0.0]
        
        vtk.vtkInteractorObserver.ComputeDisplayToWorld(renderer, x, y, 0, worldPt1)
        vtk.vtkInteractorObserver.ComputeDisplayToWorld(renderer, x, y, 1, worldPt2)
        
        return np.array(worldPt1[:3]), np.array(worldPt2[:3])
    
    def _translateAlongAxis(self, axisId, deltaX, deltaY):
        """Translate the frame along an axis using proper 3D ray-line intersection."""
        # Transform axis vector to world coordinates (like C++ version)
        # Start with unit vector along the axis
        translateAxis = np.array([0.0, 0.0, 0.0])
        translateAxis[axisId] = 1.0
        
        # Transform the vector to world coordinates
        axisDir = np.array(self.transform.TransformVector(translateAxis[0], translateAxis[1], translateAxis[2]))
        
        # Start point is the interaction start world point (fixed at press time)
        startWorldPoint = self.startWorldPoint
        lineEnd = startWorldPoint + axisDir
        
        # Get current mouse position from lastEventPosition + delta
        currentX = self.lastEventPosition[0] + deltaX
        currentY = self.lastEventPosition[1] + deltaY
        
        # Compute world ray for current mouse position
        currentRay1, currentRay2 = self._getWorldRay(currentX, currentY)
        
        # Compute intersection of mouse ray with axis line
        # Use VTK's line-line intersection
        uu = mutable(0.0)
        vv = mutable(0.0)
        
        vtk.vtkLine.Intersection(
            currentRay1.tolist(), currentRay2.tolist(),
            startWorldPoint.tolist(), lineEnd.tolist(),
            uu, vv)
        
        # Current point on axis (vv is the parameter along the axis)
        currentAxisPoint = startWorldPoint + axisDir * vv.get()
        
        # Get previous mouse position ray
        prevRay1, prevRay2 = self._getWorldRay(
            self.lastEventPosition[0], self.lastEventPosition[1])
        
        # Compute intersection for previous position
        uu2 = mutable(0.0)
        vv2 = mutable(0.0)
        vtk.vtkLine.Intersection(
            prevRay1.tolist(), prevRay2.tolist(),
            startWorldPoint.tolist(), lineEnd.tolist(),
            uu2, vv2)
        
        # Previous point on axis
        prevAxisPoint = startWorldPoint + axisDir * vv2.get()
        
        # Compute world delta
        worldDelta = currentAxisPoint - prevAxisPoint
        
        # Translate the transform
        self.transform.Translate(worldDelta[0], worldDelta[1], worldDelta[2])
        self.transform.Modified()
    
    def _rotateAboutAxis(self, axisId, deltaX, deltaY):
        """Rotate the frame about an axis (matching C++ implementation)."""
        # Get center of rotation (frame origin)
        centerOfRotation = np.array(self.transform.GetPosition())
        
        # Get view plane normal for sign determination
        camera = self.view.renderer().GetActiveCamera()
        vpn = np.array(camera.GetViewPlaneNormal())
        
        # Transform rotation axis to world coordinates
        rotateAxis = np.array([0.0, 0.0, 0.0])
        rotateAxis[axisId] = 1.0
        rotateAxisWorld = np.array(self.transform.TransformVector(rotateAxis[0], rotateAxis[1], rotateAxis[2]))
        
        # Compute the center of rotation in display coordinates
        displayCenter = [0.0, 0.0, 0.0]
        vtk.vtkInteractorObserver.ComputeWorldToDisplay(
            self.view.renderer(),
            centerOfRotation[0], centerOfRotation[1], centerOfRotation[2],
            displayCenter)
        
        # Compute rotation angle from mouse movement
        # Get current mouse position from lastEventPosition + delta
        currentX = self.lastEventPosition[0] + deltaX
        currentY = self.lastEventPosition[1] + deltaY
        
        # Create vectors from center to mouse positions
        vec1 = np.array([
            currentX - displayCenter[0],
            currentY - displayCenter[1],
            0.0
        ])
        vec2 = np.array([
            self.lastEventPosition[0] - displayCenter[0],
            self.lastEventPosition[1] - displayCenter[1],
            0.0
        ])
        
        # Normalize vectors
        vec1Norm = np.linalg.norm(vec1)
        vec2Norm = np.linalg.norm(vec2)
        
        if vec1Norm == 0.0 or vec2Norm == 0.0:
            return
        
        vec1 = vec1 / vec1Norm
        vec2 = vec2 / vec2Norm
        
        # Compute angle
        vectorDot = np.clip(np.dot(vec1, vec2), -1.0, 1.0)
        theta = np.degrees(np.arccos(vectorDot))
        
        # Determine rotation direction
        direction = np.cross(vec1, vec2)
        if direction[2] < 0.0:
            theta = -theta
        
        # Flip sign if axis is pointing towards camera
        if np.dot(vpn, rotateAxisWorld) > 0.0:
            theta = -theta
        
        # Apply rotation
        self.transform.PostMultiply()
        self.transform.Translate(-centerOfRotation[0], -centerOfRotation[1], -centerOfRotation[2])
        self.transform.RotateWXYZ(theta, rotateAxisWorld[0], rotateAxisWorld[1], rotateAxisWorld[2])
        self.transform.Translate(centerOfRotation[0], centerOfRotation[1], centerOfRotation[2])
        self.transform.PreMultiply()
        self.transform.Modified()
    
    def _translateInPlane(self, ringId, deltaX, deltaY):
        """Translate the frame in a plane using proper 3D ray-plane intersection."""
        # Get plane normal - ringId matches the axis that's normal to the plane
        # Ring 0 (YZ plane): normal = X axis (0)
        # Ring 1 (XZ plane): normal = Y axis (1)
        # Ring 2 (XY plane): normal = Z axis (2)
        planeNormal = np.array([0.0, 0.0, 0.0])
        planeNormal[ringId] = 1.0
        
        # Transform plane normal to world coordinates
        planeNormalWorld = np.array(self.transform.TransformVector(planeNormal[0], planeNormal[1], planeNormal[2]))
        
        # Start point is the interaction start world point
        startWorldPoint = self.startWorldPoint
        
        # Get current mouse position
        currentX = self.lastEventPosition[0] + deltaX
        currentY = self.lastEventPosition[1] + deltaY
        
        # Compute world ray for current mouse position
        currentRay1, currentRay2 = self._getWorldRay(currentX, currentY)
        
        # Compute intersection of mouse ray with plane
        t = vtk.mutable(0.0)
        planePoint = [0.0, 0.0, 0.0]
        vtk.vtkPlane.IntersectWithLine(
            currentRay1.tolist(), currentRay2.tolist(),
            planeNormalWorld.tolist(), startWorldPoint.tolist(),
            t, planePoint)
        
        # Get previous mouse position ray
        prevRay1, prevRay2 = self._getWorldRay(
            self.lastEventPosition[0], self.lastEventPosition[1])
        
        # Compute intersection for previous position
        t2 = vtk.mutable(0.0)
        prevPlanePoint = [0.0, 0.0, 0.0]
        vtk.vtkPlane.IntersectWithLine(
            prevRay1.tolist(), prevRay2.tolist(),
            planeNormalWorld.tolist(), startWorldPoint.tolist(),
            t2, prevPlanePoint)
        
        # Compute world delta
        worldDelta = np.array(planePoint) - np.array(prevPlanePoint)
        
        # Translate the transform
        self.transform.Translate(worldDelta[0], worldDelta[1], worldDelta[2])
        self.transform.Modified()
    
    def _rotateAboutPlaneNormal(self, ringId, deltaX, deltaY):
        """Rotate the frame about a plane normal."""
        axes = getAxesFromTransform(self.transform)
        origin = np.array(self.transform.GetPosition())
        
        # Get plane normal (ringId 0=Z, 1=X, 2=Y)
        normal = axes[2] if ringId == 0 else (axes[0] if ringId == 1 else axes[1])
        
        # Rotation angle
        angle = np.sqrt(deltaX**2 + deltaY**2) * 0.5
        rotationAxis = normal
        
        # Create rotation transform
        rotation = vtk.vtkTransform()
        rotation.PostMultiply()
        rotation.Translate(-origin[0], -origin[1], -origin[2])
        rotation.RotateWXYZ(angle if deltaX + deltaY > 0 else -angle, rotationAxis)
        rotation.Translate(origin[0], origin[1], origin[2])
        
        # Apply rotation
        self.transform.PostMultiply()
        self.transform.Concatenate(rotation)
        self.transform.PreMultiply()
    
    def onMouseMove(self, event):
        """Handle mouse move for hover highlighting and interaction."""
        pos = self.getMousePositionInView(event)
        
        # Initialize lastEventPosition if not set
        if self.lastEventPosition == [0.0, 0.0] and self.interactionState == self.OUTSIDE:
            self.lastEventPosition = [pos[0], pos[1]]
            return False
        
        deltaX = pos[0] - self.lastEventPosition[0]
        deltaY = pos[1] - self.lastEventPosition[1]
        
        consumed = False
        
        if self.interactionState == self.OUTSIDE:
            # Hover highlighting
            pickedType, pickedId = self._pickActor(pos[0], pos[1])
            if pickedType is not None:
                self._updateHighlight(pickedType, pickedId)
                self.view.render()
                consumed = True  # Consume if hovering over widget
        elif self.interactionState == self.TRANSLATING:
            # Translating along axis
            if 0 <= self.interactingAxis < 3:
                self._translateAlongAxis(self.interactingAxis, deltaX, deltaY)
                self.view.render()
                consumed = True
        elif self.interactionState == self.TRANSLATING_IN_PLANE:
            # Translating in plane
            if 0 <= self.interactingAxis < 3:
                self._translateInPlane(self.interactingAxis, deltaX, deltaY)
                self.view.render()
                consumed = True
        elif self.interactionState == self.ROTATING:
            # Rotating about axis
            # For rings, interactingAxis is already the axis ID (0=X, 1=Y, 2=Z)
            # Ring 0 (YZ plane) rotates about X axis (0)
            # Ring 1 (XZ plane) rotates about Y axis (1)
            # Ring 2 (XY plane) rotates about Z axis (2)
            if 0 <= self.interactingAxis < 3:
                self._rotateAboutAxis(self.interactingAxis, deltaX, deltaY)
                self.view.render()
                consumed = True
        
        self.lastEventPosition = [pos[0], pos[1]]
        return consumed
    
    def onLeftMousePress(self, event):
        """Handle left mouse press - start translation."""
        pos = self.getMousePositionInView(event)
        self.lastEventPosition = [pos[0], pos[1]]
        self.startEventPosition = [pos[0], pos[1]]
        
        pickedType, pickedId = self._pickActor(pos[0], pos[1])
        
        if pickedType == 'axis':
            self.interactionState = self.TRANSLATING
            self.interactingAxis = pickedId
            # Store the interaction start world point (frame origin at press time)
            self.startWorldPoint = np.array(self.transform.GetPosition())
            return True  # Consume event
        elif pickedType == 'ring':
            self.interactionState = self.TRANSLATING_IN_PLANE
            self.interactingAxis = pickedId
            self.startWorldPoint = np.array(self.transform.GetPosition())
            return True  # Consume event
        else:
            self.interactionState = self.OUTSIDE
            return False  # Don't consume - allow camera interactor
    
    def onRightMousePress(self, event):
        """Handle right mouse press - start rotation."""
        pos = self.getMousePositionInView(event)
        self.lastEventPosition = [pos[0], pos[1]]
        self.startEventPosition = [pos[0], pos[1]]
        
        pickedType, pickedId = self._pickActor(pos[0], pos[1])
        
        if pickedType == 'axis':
            self.interactionState = self.ROTATING
            self.interactingAxis = pickedId  # 0-2 for axes, rotate about this axis
            return True  # Consume event
        elif pickedType == 'ring':
            self.interactionState = self.ROTATING
            # Ring rotation: ring 0 (YZ plane) rotates about X axis (0)
            #               ring 1 (XZ plane) rotates about Y axis (1)
            #               ring 2 (XY plane) rotates about Z axis (2)
            self.interactingAxis = pickedId  # Ring ID matches the axis to rotate about
            return True  # Consume event
        else:
            self.interactionState = self.OUTSIDE
            return False  # Don't consume - allow camera interactor
    
    def onLeftMouseRelease(self, event):
        """Handle left mouse release."""
        consumed = False
        if self.interactionState in (self.TRANSLATING, self.TRANSLATING_IN_PLANE):
            self.interactionState = self.OUTSIDE
            self.interactingAxis = -1
            consumed = True
        return consumed
    
    def onRightMouseRelease(self, event):
        """Handle right mouse release."""
        consumed = False
        if self.interactionState == self.ROTATING:
            self.interactionState = self.OUTSIDE
            self.interactingAxis = -1
            consumed = True
        return consumed
    
    def setEnabled(self, enabled):
        """Enable or disable the widget."""
        visibility = 1 if enabled else 0
        for actor in self.axisActors + self.ringActors:
            actor.SetVisibility(visibility)
        self.view.render()
    
    def cleanup(self):
        """Clean up and remove actors."""
        renderer = self.view.renderer()
        for actor in self.axisActors + self.ringActors:
            renderer.RemoveActor(actor)
        self.removeEventFilter()
        self.view.render()

