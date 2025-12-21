"""Python implementation of vtkGridSource filter."""

import director.vtkAll as vtk
from director.shallowCopy import shallowCopy


def makeGridPolyData(
    gridHalfWidth=100,
    majorTickSize=10.0,
    minorTickSize=1.0,
    majorGridRings=True,
    minorGridRings=False,
    origin=(0, 0, 0),
    normal=(0, 0, 1),
):
    """
    Create grid PolyData (Python reimplementation of vtkGridSource).

    Parameters:
    -----------
    gridHalfWidth : float
        Half width of the grid
    majorTickSize : float
        Size of major grid ticks
    minorTickSize : float
        Size of minor grid ticks
    majorGridRings : bool
        Whether to show major tick rings (arcs)
    minorGridRings : bool
        Whether to show minor tick rings (arcs)
    origin : tuple
        Origin point of the grid (x, y, z)
    normal : tuple
        Normal vector for the grid plane (x, y, z)

    Returns:
    --------
    vtkPolyData : The grid geometry
    """
    gridSize = int(gridHalfWidth / majorTickSize)

    # Create plane source for the grid surface/edges
    plane = vtk.vtkPlaneSource()
    plane.SetOrigin(-gridHalfWidth, -gridHalfWidth, 0.0)
    plane.SetPoint1(gridHalfWidth, -gridHalfWidth, 0.0)
    plane.SetPoint2(-gridHalfWidth, gridHalfWidth, 0.0)
    plane.SetResolution(gridSize * 2, gridSize * 2)
    plane.SetCenter(origin)
    plane.SetNormal(normal)

    # Extract edges from the plane
    edges = vtk.vtkExtractEdges()
    edges.SetInputConnection(plane.GetOutputPort())

    # Append data sources
    append = vtk.vtkAppendPolyData()

    # Add surface or edges based on SurfaceEnabled equivalent
    # For grid, we typically want edges (wireframe)
    # But we'll add surface if needed (this matches vtkGridSource behavior)
    # For now, always add edges (typical grid use case)
    append.AddInputConnection(edges.GetOutputPort())

    # Add major tick rings if enabled
    if majorGridRings:
        for i in range(1, gridSize + 1):
            ring = vtk.vtkRegularPolygonSource()
            ring.GeneratePolygonOff()
            ring.SetNumberOfSides(360)
            ring.SetRadius(i * majorTickSize)
            ring.SetCenter(origin)
            # Note: RegularPolygonSource creates in XY plane,
            # we'd need to transform if normal is different
            append.AddInputConnection(ring.GetOutputPort())

    # Create minor grid if different size
    if minorTickSize != majorTickSize:
        minorGridSize = int(gridHalfWidth / minorTickSize)

        # Minor grid plane
        minorPlane = vtk.vtkPlaneSource()
        minorPlane.SetOrigin(-gridHalfWidth, -gridHalfWidth, 0.0)
        minorPlane.SetPoint1(gridHalfWidth, -gridHalfWidth, 0.0)
        minorPlane.SetPoint2(-gridHalfWidth, gridHalfWidth, 0.0)
        minorPlane.SetResolution(minorGridSize * 2, minorGridSize * 2)
        minorPlane.SetCenter(origin)
        minorPlane.SetNormal(normal)

        minorEdges = vtk.vtkExtractEdges()
        minorEdges.SetInputConnection(minorPlane.GetOutputPort())
        append.AddInputConnection(minorEdges.GetOutputPort())

        # Add minor tick rings if enabled
        if minorGridRings:
            for i in range(1, minorGridSize + 1):
                ring = vtk.vtkRegularPolygonSource()
                ring.GeneratePolygonOff()
                ring.SetNumberOfSides(360)
                ring.SetRadius(i * minorTickSize)
                ring.SetCenter(origin)
                append.AddInputConnection(ring.GetOutputPort())

    append.Update()
    return shallowCopy(append.GetOutput())
