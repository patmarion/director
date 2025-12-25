from director import mainwindowapp
from director import visualization as vis
from director.vtk_widget import VTKWidget

fields = mainwindowapp.construct()


view2 = VTKWidget()
view2.initializeGrid()
view2.initializeViewBehaviors()
fields.app.splitter.addWidget(view2)

fields.app.start()
