import PythonQt
from PythonQt import QtCore, QtGui
from director import objectmodel as om


class SettingsWidget:
    def __init__(self):
        self.treeWidget =  QtGui.QTreeWidget()
        self.propertiesPanel = PythonQt.dd.ddPropertiesPanel()
        self.objectModel = om.ObjectModelTree()
        self.objectModel.init(self.treeWidget, self.propertiesPanel)
        self.treeWidget.setColumnHidden(1, True)
        self.widget = QtGui.QWidget()
        self.widget.setWindowTitle('Settings')

        self.rightWidget = QtGui.QWidget()
        self.groupBox = QtGui.QGroupBox('Settings')
        l = QtGui.QHBoxLayout(self.widget)
        l.addWidget(self.treeWidget)
        l.addWidget(self.rightWidget)


        rl = QtGui.QVBoxLayout(self.rightWidget)
        rl.addWidget(self.groupBox)
        rl.addWidget(QtGui.QPushButton('Ok'))

        gl = QtGui.QVBoxLayout(self.groupBox)
        gl.addWidget(self.propertiesPanel)
        gl.addStretch()

        self.treeWidget.setFixedWidth(200)
        self.propertiesPanel.setMinimumWidth(300)

        general = om.ObjectModelItem('General', icon='')
        self.objectModel.addToObjectModel(general)

        obj = om.ObjectModelItem('Background', icon='')
        self.objectModel.addToObjectModel(obj, parentObj=general)
        self.objectModel.setActiveObject(obj)


if __name__ == '__main__':
    s = SettingsWidget()
    s.widget.show()
