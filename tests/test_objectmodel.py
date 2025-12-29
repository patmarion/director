"""Tests for objectmodel module."""

from qtpy.QtWidgets import QTreeView

from director.objectmodel import ObjectModelItem, ObjectModelTree
from director.propertiespanel import PropertiesPanel


def test_object_model_tree_construction(qapp):
    """Test that ObjectModelTree can be constructed."""
    tree = ObjectModelTree()
    assert tree is not None


def test_object_model_tree_init(qapp):
    """Test that ObjectModelTree can be initialized with QTreeView and dummy PropertiesPanel."""
    tree = ObjectModelTree()
    tree_view = QTreeView()

    # Should not raise
    properties_panel = PropertiesPanel()
    tree.init(tree_view, properties_panel)

    assert tree.getTreeView() == tree_view
    assert tree.getPropertiesPanel() == properties_panel


def test_object_model_tree_show(qapp):
    """Test that ObjectModelTree can be shown in a widget."""
    from qtpy.QtWidgets import QVBoxLayout, QWidget

    widget = QWidget()
    layout = QVBoxLayout(widget)

    tree = ObjectModelTree()

    layout.addWidget(tree.getTreeView())

    widget.show()
    assert widget.isVisible()
    widget.close()


def test_object_model_item_creation(qapp):
    """Test that ObjectModelItem can be created."""
    item = ObjectModelItem("Test Item")
    assert item is not None
    assert item.getProperty("Name") == "Test Item"


def test_object_model_add_and_show(qapp):
    """Test adding an item to the object model and showing it."""
    from qtpy.QtWidgets import QVBoxLayout, QWidget

    widget = QWidget()
    layout = QVBoxLayout(widget)

    tree = ObjectModelTree()

    tree.init()
    layout.addWidget(tree.getTreeView())

    # Create and add an item
    item = ObjectModelItem("Test Object")
    tree.addToObjectModel(item)

    widget.show()

    # Verify item was added
    objects = tree.getObjects()
    assert len(objects) == 1
    assert objects[0] == item

    widget.close()


def test_object_model_property_change_updates_tree_item(qapp):
    """Test that changing a property on an object updates the QStandardItem."""
    tree = ObjectModelTree()

    tree.init()

    # Create and add an item
    obj = ObjectModelItem("original name")
    tree.addToObjectModel(obj)

    # Verify initial name is set correctly - access via itemModel
    tree_item = tree.itemModel.item(0, 0)
    assert tree_item is not None
    assert tree_item.text() == "original name"

    # Change the name property using setProperty
    obj.setProperty("Name", "new name")

    # Verify the tree item text has been updated
    assert tree_item.text() == "new name"

    # Also verify the property was actually changed
    assert obj.getProperty("Name") == "new name"

    # Test direct property access via properties attribute (using alternate name)
    obj.properties.name = "another name"

    # Verify the tree item text has been updated again
    assert tree_item.text() == "another name"
    assert obj.getProperty("Name") == "another name"
