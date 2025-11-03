"""Tests for objectmodel module."""

import sys
import pytest
from qtpy.QtWidgets import QApplication, QTreeWidget
from director.objectmodel import ObjectModelTree, ObjectModelItem


class DummyPropertiesPanel:
    """Dummy properties panel for testing."""
    
    def clear(self):
        """Clear the panel."""
        pass
    
    def setBrowserModeToWidget(self):
        """Set browser mode to widget."""
        pass


def test_object_model_tree_construction(qapp):
    """Test that ObjectModelTree can be constructed."""
    tree = ObjectModelTree()
    assert tree is not None


def test_object_model_tree_init(qapp):
    """Test that ObjectModelTree can be initialized with QTreeWidget and dummy PropertiesPanel."""
    tree = ObjectModelTree()
    tree_widget = QTreeWidget()
    properties_panel = DummyPropertiesPanel()
    
    # Should not raise
    tree.init(tree_widget, properties_panel)
    
    assert tree.getTreeWidget() == tree_widget
    assert tree.getPropertiesPanel() == properties_panel


def test_object_model_tree_show(qapp):
    """Test that ObjectModelTree can be shown in a widget."""
    from qtpy.QtWidgets import QWidget, QVBoxLayout
    
    widget = QWidget()
    layout = QVBoxLayout(widget)
    
    tree = ObjectModelTree()
    tree_widget = QTreeWidget()
    properties_panel = DummyPropertiesPanel()
    
    tree.init(tree_widget, properties_panel)
    layout.addWidget(tree_widget)
    
    widget.show()
    qapp.processEvents()
    
    assert widget.isVisible()
    widget.close()


def test_object_model_item_creation(qapp):
    """Test that ObjectModelItem can be created."""
    item = ObjectModelItem("Test Item")
    assert item is not None
    assert item.getProperty('Name') == "Test Item"


def test_object_model_add_and_show(qapp):
    """Test adding an item to the object model and showing it."""
    from qtpy.QtWidgets import QWidget, QVBoxLayout
    
    widget = QWidget()
    layout = QVBoxLayout(widget)
    
    tree = ObjectModelTree()
    tree_widget = QTreeWidget()
    properties_panel = DummyPropertiesPanel()
    
    tree.init(tree_widget, properties_panel)
    layout.addWidget(tree_widget)
    
    # Create and add an item
    item = ObjectModelItem("Test Object")
    tree.addToObjectModel(item)
    
    widget.show()
    qapp.processEvents()
    
    # Verify item was added
    objects = tree.getObjects()
    assert len(objects) == 1
    assert objects[0] == item
    
    widget.close()
    qapp.processEvents()


def test_object_model_property_change_updates_tree_item(qapp):
    """Test that changing a property on an object updates the QTreeWidgetItem."""
    tree = ObjectModelTree()
    tree_widget = QTreeWidget()
    properties_panel = DummyPropertiesPanel()
    
    tree.init(tree_widget, properties_panel)
    
    # Create and add an item
    obj = ObjectModelItem("original name")
    tree.addToObjectModel(obj)
    
    # Process events to ensure tree widget is updated
    qapp.processEvents()
    
    # Verify initial name is set correctly
    tree_item = tree_widget.topLevelItem(0)
    assert tree_item is not None
    assert tree_item.text(0) == "original name"
    
    # Change the name property using setProperty
    obj.setProperty('Name', 'new name')
    
    # Process events to allow signal/slot connections to propagate
    qapp.processEvents()
    
    # Verify the tree widget item text has been updated
    assert tree_item.text(0) == "new name"
    
    # Also verify the property was actually changed
    assert obj.getProperty('Name') == "new name"
    
    # Test direct property access via properties attribute (using alternate name)
    obj.properties.name = "another name"
    
    # Process events again
    qapp.processEvents()
    
    # Verify the tree widget item text has been updated again
    assert tree_item.text(0) == "another name"
    assert obj.getProperty('Name') == "another name"

