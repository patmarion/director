from director.propertiespanel import EnumEditor, IntEditor, LabelEditor, PropertiesPanel
from director.propertyset import PropertyAttributes, PropertySet


def test_properties_panel_uses_label_editor_for_read_only_and_hidden_properties(qapp):
    props = PropertySet()
    props.addProperty("Read Only Value", "ready", attributes=PropertyAttributes(readOnly=True))
    props.addProperty("Hidden Count", 3, attributes=PropertyAttributes(hidden=True))

    panel = PropertiesPanel()
    panel.connectProperties(props)

    read_only_item = panel.propertyToItem["Read Only Value"]
    hidden_item = panel.propertyToItem["Hidden Count"]

    assert isinstance(panel.itemToEditor[read_only_item], LabelEditor)
    assert isinstance(panel.itemToEditor[hidden_item], LabelEditor)
    assert hidden_item.isHidden()


def test_properties_panel_rebuilds_editor_when_read_only_changes(qapp):
    props = PropertySet()
    props.addProperty("Count", 5)

    panel = PropertiesPanel()
    panel.connectProperties(props)

    item = panel.propertyToItem["Count"]
    assert isinstance(panel.itemToEditor[item], IntEditor)

    props.setPropertyAttribute("Count", "readOnly", True)
    assert isinstance(panel.itemToEditor[item], LabelEditor)

    props.setPropertyAttribute("Count", "readOnly", False)
    assert isinstance(panel.itemToEditor[item], IntEditor)


def test_read_only_enum_uses_enum_label_and_rebuilds_to_combo_box(qapp):
    props = PropertySet()
    props.addProperty(
        "Mode",
        2,
        attributes=PropertyAttributes(readOnly=True, enumNames=["Off", "On", "Auto"]),
    )

    panel = PropertiesPanel()
    panel.connectProperties(props)

    item = panel.propertyToItem["Mode"]
    editor = panel.itemToEditor[item]
    assert isinstance(editor, LabelEditor)
    assert editor.label.text() == "Auto"

    props.setPropertyAttribute("Mode", "readOnly", False)
    assert isinstance(panel.itemToEditor[item], EnumEditor)
