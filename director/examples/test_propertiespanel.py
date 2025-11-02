"""Test program for PropertiesPanel - shows two panels synced to the same PropertySet."""

import sys
from qtpy.QtWidgets import QApplication, QDockWidget, QSplitter
from qtpy.QtCore import Qt
from director import objectmodel as om
from director.propertyset import PropertyAttributes
from director.propertiespanel import PropertiesPanel
from director.mainwindow import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('test_propertiespanel')
    
    # Create a main window
    main_window = MainWindow("Property Panel Test")
    
    # Create an ObjectModelItem with various properties
    obj = om.ObjectModelItem('test')
    
    # Float properties with different decimal precision and step sizes
    obj.addProperty('double_precise', 1.0, attributes=PropertyAttributes(decimals=5, minimum=0, maximum=100, singleStep=0.001))
    obj.addProperty('double_rounded', 1.0, attributes=PropertyAttributes(decimals=2, minimum=0, maximum=100, singleStep=0.1))
    obj.addProperty('double_large_step', 10.0, attributes=PropertyAttributes(decimals=1, minimum=-1000, maximum=1000, singleStep=10.0))
    
    # Integer properties with different ranges and step sizes
    obj.addProperty('int_small', 1, attributes=PropertyAttributes(minimum=0, maximum=10, singleStep=1))
    obj.addProperty('int_medium', 50, attributes=PropertyAttributes(minimum=0, maximum=100, singleStep=5))
    obj.addProperty('int_large', 500, attributes=PropertyAttributes(minimum=0, maximum=1000, singleStep=10))
    
    # Enum properties (integer with enumNames attribute)
    obj.addProperty('enum_choice', 0, attributes=PropertyAttributes(enumNames=['Option A', 'Option B', 'Option C', 'Option D']))
    obj.addProperty('quality', 1, attributes=PropertyAttributes(enumNames=['Low', 'Medium', 'High', 'Ultra']))
    
    # Arrays with attributes
    obj.addProperty('double list', [1.0, 2.0, 3.0], attributes=PropertyAttributes(decimals=2, minimum=0, maximum=100, singleStep=0.5))
    obj.addProperty('int list', [1, 2, 3], attributes=PropertyAttributes(minimum=0, maximum=100, singleStep=1))
    obj.addProperty('bool list', [True, False, True, False])
    obj.addProperty('string list', ['first', 'second', 'third', 'fourth'])
    
    # Basic properties
    obj.addProperty('bool', True)
    obj.addProperty('str', 'value')
    obj.addProperty('color', [1.0, 0.5, 0.0])
    
    # Nested properties
    obj.addProperty('nest1/prop1', 42)
    obj.addProperty('nest1/prop2', 'nested value')
    obj.addProperty('nest1/enum_nested', 0, attributes=PropertyAttributes(enumNames=['First', 'Second', 'Third']))
    obj.addProperty('nest2/level1/prop3', 3.14)
    obj.addProperty('nest2/level1/float_precise', 1.23456, attributes=PropertyAttributes(decimals=4, minimum=0, maximum=10, singleStep=0.0001))
    
    # Create two property panels, both connected to the same PropertySet
    panel1 = PropertiesPanel()
    panel1.connectProperties(obj.properties)
    
    panel2 = PropertiesPanel()
    panel2.connectProperties(obj.properties)
    
    # Create a widget to hold both panels side by side
    splitter = QSplitter()
    splitter.addWidget(panel1)
    splitter.addWidget(panel2)
    splitter.setSizes([400, 400])
    
    # Add the splitter as a dock widget
    dock = QDockWidget("Property Panels", main_window)
    dock.setWidget(splitter)
    dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
    main_window.addDockWidget(Qt.RightDockWidgetArea, dock)
    
    # Show Python console for interactive testing
    main_window._toggle_python_console()
    
    # Add obj to console namespace for interactive testing
    if main_window._python_console_dock:
        console_widget = main_window._python_console_dock.widget()
        if hasattr(console_widget, 'kernel_manager') and console_widget.kernel_manager:
            console_widget.kernel_manager.kernel.shell.push({'obj': obj})
    
    # Show the main window
    main_window.show()
    
    print("Two property panels are shown, both connected to the same PropertySet.")
    print("Edit values in one panel and watch them update in the other!")
    print("")
    print("Property attributes being tested:")
    print("  - Float properties with different decimals (5, 2, 1, 4)")
    print("  - Float properties with different step sizes (0.001, 0.5, 10.0, 1.0)")
    print("  - Integer properties with different ranges (0-10, 0-100, 0-1000)")
    print("  - Integer properties with different step sizes (1, 5, 10)")
    print("  - Enum properties with enumNames (combo boxes)")
    print("  - Properties with sliders (when range <= 1000)")
    print("  - Nested properties with attributes")
    print("")
    print("You can also edit properties programmatically in the Python console:")
    print("  obj.properties.double_precise = 3.14159")
    print("  obj.properties.enum_choice = 2  # or obj.properties.enum_choice = 'Option C'")
    print("  obj.properties.int_with_slider = 75")
    print()
    print("Test property removal:")
    print("  obj.properties.removeProperty('str')  # Should disappear from both panels")
    print()
    print("Test attribute changes (enumNames):")
    print("  obj.properties.setPropertyAttribute('enum_choice', 'enumNames', ['New A', 'New B', 'New C'])")
    print("  obj.properties.color = [0.0, 1.0, 0.5]")
    print("  obj.properties.bool = False")
    
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())

