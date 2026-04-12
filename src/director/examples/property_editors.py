"""Test program for PropertiesPanel - shows two panels synced to the same PropertySet."""

import sys

from qtpy.QtWidgets import QApplication, QSplitter

from director.propertiespanel import PropertiesPanel
from director.propertyset import PropertyAttributes, PropertySet


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
        "enum_choice",
        0,
        attributes=PropertyAttributes(
            enumNames=["Option A", "Option B", "Option C", "Option D"],
            docstring="Select an option from the list.",
        ),
    )
    props.addProperty(
        "quality",
        1,
        attributes=PropertyAttributes(
            enumNames=["Low", "Medium", "High", "Ultra"],
            docstring="Quality setting used for rendering.",
        ),
    )

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
    props.addProperty("bool", True, attributes=PropertyAttributes(docstring="Enable or disable the feature."))
    props.addProperty("str", "value", attributes=PropertyAttributes(docstring="Free-form text value."))
    props.addProperty("color", [1.0, 0.5, 0.0])
    props.addProperty(
        "debug payload",
        {"checksum": "0xdeadbeef", "valid": True},
        attributes=PropertyAttributes(
            readOnly=True,
            hidden=True,
            docstring="Hidden properties can stay out of the UI until you choose to reveal them.",
        ),
    )

    # Read-only property examples with a live toggle for the readOnly attribute
    props.addProperty(
        "read-only/use label editors",
        True,
        attributes=PropertyAttributes(
            docstring="Toggle this checkbox to switch the read-only demo properties between labels and editable widgets."
        ),
    )
    props.addProperty(
        "read-only/int value",
        7,
        attributes=PropertyAttributes(
            readOnly=True,
            minimum=0,
            maximum=20,
            singleStep=1,
            docstring="Read-only integer rendered as a label until the toggle is disabled.",
        ),
    )
    props.addProperty(
        "read-only/double list",
        [0.25, 1.5, 2.75],
        attributes=PropertyAttributes(
            readOnly=True,
            decimals=3,
            minimum=-10,
            maximum=10,
            singleStep=0.125,
            docstring="Read-only list of doubles. Disable the toggle above to edit each element.",
        ),
    )
    props.addProperty(
        "read-only/string value",
        "Label mode",
        attributes=PropertyAttributes(
            readOnly=True,
            docstring="Read-only string rendered as a label until the toggle is disabled.",
        ),
    )
    props.addProperty(
        "read-only/enum value",
        2,
        attributes=PropertyAttributes(
            readOnly=True,
            enumNames=["Low", "Medium", "High", "Ultra"],
            docstring="Read-only enums now show their label instead of the stored integer index.",
        ),
    )
    props.addProperty(
        "read-only/opaque dict",
        {"source": "demo", "frame_count": 2},
        attributes=PropertyAttributes(
            readOnly=True,
            docstring="Opaque values like dicts always use labels because the panel has no editor widget for them.",
        ),
    )

    # Nested properties
    props.addProperty("nest1/prop1", 42, attributes=PropertyAttributes(docstring="Nested integer property."))
    props.addProperty("nest1/prop2", "nested value", attributes=PropertyAttributes(docstring="Nested string."))
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

    read_only_demo_properties = [
        "read-only/int value",
        "read-only/double list",
        "read-only/string value",
        "read-only/enum value",
        "read-only/opaque dict",
    ]

    def update_read_only_demo(use_label_editors):
        for property_name in read_only_demo_properties:
            props.setPropertyAttribute(property_name, "readOnly", bool(use_label_editors))

    props.connectPropertyValueChanged("read-only/use label editors", update_read_only_demo)
    update_read_only_demo(props.getProperty("read-only/use label editors"))

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
    print("  - Read-only values rendered as labels")
    print("  - A read-only/ group with a live checkbox that toggles label/edit mode")
    print("  - Hidden properties that can be revealed later")
    print("  - Properties with docstring tooltips (hover the label/value)")
    print("")
    print("You can also edit properties programmatically in Python:")
    print("  props.double_precise = 3.14159")
    print("  props.enum_choice = 2")
    print("  props.setProperty('read-only/use label editors', False)")
    print("  props.setProperty('read-only/string value', 'Editable mode')")
    print("  props.setProperty('read-only/enum value', 1)  # label mode shows 'Medium'")
    print()
    print("Test property removal:")
    print("  props.removeProperty('str')  # Should disappear from both panels")
    print()
    print("Test attribute changes (enumNames):")
    print("  props.setPropertyAttribute('enum_choice', 'enumNames', ['New A', 'New B', 'New C'])")
    print("  props.setPropertyAttribute('debug payload', 'hidden', False)")
    print("  props.setPropertyAttribute('double_precise', 'readOnly', True)")
    print("  # The dict demo remains a label even when readOnly is False.")
    print("  props.color = [0.0, 1.0, 0.5]")
    print("  props.bool = False")

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
