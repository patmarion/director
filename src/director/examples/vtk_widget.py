from qtpy.QtWidgets import QApplication

from director.vtk_widget import VTKWidget

app = QApplication([])

widget = VTKWidget()
widget.initializeGrid()
widget.show()
app.exec_()
