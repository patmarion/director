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


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for tests."""
    if not QApplication.instance():
        app = QApplication(sys.argv)
        yield app
        app.quit()
    else:
        yield QApplication.instance()


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

