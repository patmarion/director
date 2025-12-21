"""Test program for PropertiesPanel - shows two panels synced to the same PropertySet."""

import sys
from qtpy.QtWidgets import QApplication, QSplitter
from director.propertyset import PropertySet, PropertyAttributes
from director.propertiespanel import PropertiesPanel


def main():
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Property Panel Test")

    # Create a PropertySet with various properties
    props = PropertySet()

    # Float properties with different decimal precision and step sizes
    props.addProperty(
        "double_precise", 1.0, attributes=PropertyAttributes(decimals=5, minimum=0, maximum=100, singleStep=0.001)
    )
    props.addProperty(
        "double_rounded", 1.0, attributes=PropertyAttributes(decimals=2, minimum=0, maximum=100, singleStep=0.1)
    )
    props.addProperty(
        "double_large_step",
        10.0,
        attributes=PropertyAttributes(decimals=1, minimum=-1000, maximum=1000, singleStep=10.0),
    )

    # Integer properties with different ranges and step sizes
    props.addProperty("int_small", 1, attributes=PropertyAttributes(minimum=0, maximum=10, singleStep=1))
    props.addProperty("int_medium", 50, attributes=PropertyAttributes(minimum=0, maximum=100, singleStep=5))
    props.addProperty("int_large", 500, attributes=PropertyAttributes(minimum=0, maximum=1000, singleStep=10))

    # Enum properties (integer with enumNames attribute)
    props.addProperty(
        "enum_choice", 0, attributes=PropertyAttributes(enumNames=["Option A", "Option B", "Option C", "Option D"])
    )
    props.addProperty("quality", 1, attributes=PropertyAttributes(enumNames=["Low", "Medium", "High", "Ultra"]))

    # Arrays with attributes
    props.addProperty(
        "double list",
        [1.0, 2.0, 3.0],
        attributes=PropertyAttributes(decimals=2, minimum=0, maximum=100, singleStep=0.5),
    )
    props.addProperty("int list", [1, 2, 3], attributes=PropertyAttributes(minimum=0, maximum=100, singleStep=1))
    props.addProperty("bool list", [True, False, True, False])
    props.addProperty("string list", ["first", "second", "third", "fourth"])

    # Basic properties
    props.addProperty("bool", True)
    props.addProperty("str", "value")
    props.addProperty("color", [1.0, 0.5, 0.0])

    # Nested properties
    props.addProperty("nest1/prop1", 42)
    props.addProperty("nest1/prop2", "nested value")
    props.addProperty("nest1/enum_nested", 0, attributes=PropertyAttributes(enumNames=["First", "Second", "Third"]))
    props.addProperty("nest2/level1/prop3", 3.14)
    props.addProperty(
        "nest2/level1/float_precise",
        1.23456,
        attributes=PropertyAttributes(decimals=4, minimum=0, maximum=10, singleStep=0.0001),
    )

    # Create two property panels, both connected to the same PropertySet
    panel1 = PropertiesPanel()
    panel1.connectProperties(props)

    panel2 = PropertiesPanel()
    panel2.connectProperties(props)

    # Create a widget to hold both panels side by side
    splitter = QSplitter()
    splitter.addWidget(panel1)
    splitter.addWidget(panel2)
    splitter.setSizes([400, 400])
    splitter.setWindowTitle("Property Panels")
    splitter.resize(900, 600)
    splitter.show()

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
    print("You can also edit properties programmatically in Python:")
    print("  props.double_precise = 3.14159")
    print("  props.enum_choice = 2")
    print()
    print("Test property removal:")
    print("  props.removeProperty('str')  # Should disappear from both panels")
    print()
    print("Test attribute changes (enumNames):")
    print("  props.setPropertyAttribute('enum_choice', 'enumNames', ['New A', 'New B', 'New C'])")
    print("  props.color = [0.0, 1.0, 0.5]")
    print("  props.bool = False")

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
