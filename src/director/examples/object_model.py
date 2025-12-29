from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from director.objectmodel import ObjectModelItem, ObjectModelTree
from director.propertiespanel import PropertiesPanel
from director.propertyset import PropertyAttributes

app = QApplication([])

# Initialize the object model
model = ObjectModelTree()
model.init()

# Create and add some objects
obj = ObjectModelItem("parent")
child = ObjectModelItem("child")
model.addToObjectModel(obj)
model.addToObjectModel(child, parentObj=obj)

# Add properties to the objects
obj.addProperty("Bool Prop", True)
obj.addProperty("Float Prop", 1.23)
obj.addProperty("Str Prop", "hello")
child.addProperty("Enum Prop", 0, PropertyAttributes(enumNames=["Off", "On"]))

# Connect a properties panel to the object model
panel = PropertiesPanel()
model.setPropertiesPanel(panel)

# Create a widget to hold the object model and properties panel
widget = QWidget()
widget.setWindowTitle("Object Model")
layout = QVBoxLayout(widget)
layout.addWidget(model.getTreeView())
layout.addWidget(model.getPropertiesPanel())
widget.show()

# Programmatically set selection and adjust properties
model.setSelectedObject(child)
child.properties.enum_prop = "On"

# Demonstrate object look up
assert child is model.findObjectByName("child")
assert child is model.findObjectByPath("parent/child")
assert child is model.findObjectByPathList(["parent", "child"])


app.exec_()
