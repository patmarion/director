import json

import numpy as np
import pytest

from director.propertyset import PropertyAttributes, PropertySet


def create_sample_property_set():
    props = PropertySet()
    props.addProperty(
        "Position",
        [0.0, 1.0, 2.0],
        attributes=PropertyAttributes(decimals=3, minimum=-10, maximum=10),
    )
    props.addProperty(
        "Visible",
        True,
        attributes=PropertyAttributes(readOnly=False, hidden=False),
    )
    props.addProperty(
        "Name",
        "frame1",
        attributes=PropertyAttributes(readOnly=True),
    )
    return props


def test_state_round_trip_merge():
    props = create_sample_property_set()
    state = props.get_state_dict()

    # Modify properties to ensure state is restored
    props.setProperty("Position", [5.0, 5.0, 5.0])
    props.setProperty("Visible", False)

    props.restore_from_state_dict(state, merge=True)

    assert props.getProperty("Position") == (0.0, 1.0, 2.0)
    assert props.getProperty("Visible") is True
    assert props.getProperty("Name") == "frame1"


def test_restore_with_merge_adds_missing_property():
    props = PropertySet()
    props.addProperty("Existing", 1)

    state = {
        "properties": {"Existing": 5, "Added": 99},
        "attributes": {
            "Existing": {"minimum": -1, "maximum": 10},
            "Added": {"hidden": True},
        },
    }

    props.restore_from_state_dict(state, merge=True)

    assert props.getProperty("Existing") == 5
    assert props.getProperty("Added") == 99
    assert props.getPropertyAttribute("Added", "hidden") is True


def test_restore_with_merge_validates_types():
    props = PropertySet()
    props.addProperty("Color", [1.0, 0.0, 0.0])

    bad_state = {
        "properties": {"Color": [1.0, 0.0]},
        "attributes": {"Color": {}},
    }

    with pytest.raises(ValueError):
        props.restore_from_state_dict(bad_state, merge=True)


def test_restore_without_merge_requires_empty():
    props = create_sample_property_set()
    state = props.get_state_dict()

    fresh_props = PropertySet()
    fresh_props.restore_from_state_dict(state, merge=False)

    assert fresh_props.getProperty("Name") == "frame1"
    assert fresh_props.getProperty("Visible") is True

    with pytest.raises(AssertionError):
        props.restore_from_state_dict(state, merge=False)


def test_state_dict_is_json_serializable():
    props = create_sample_property_set()
    state = props.get_state_dict()
    json_data = json.dumps(state)
    restored = json.loads(json_data)

    new_props = PropertySet()
    new_props.restore_from_state_dict(restored, merge=False)

    assert new_props.getProperty("Position") == (0.0, 1.0, 2.0)
    assert new_props.getPropertyAttribute("Position", "decimals") == 3


def test_sequence_values_normalized_to_tuple():
    props = PropertySet()
    props.addProperty("Vector", [1, 2, 3])
    assert props.getProperty("Vector") == (1, 2, 3)

    props.setProperty("Vector", np.array([4.0, 5.0, 6.0]))
    assert props.getProperty("Vector") == (4.0, 5.0, 6.0)

    state = props.get_state_dict()
    restored = PropertySet()
    restored.restore_from_state_dict(state, merge=False)
    assert restored.getProperty("Vector") == (4.0, 5.0, 6.0)


def test_numeric_assignment_preserves_type():
    props = PropertySet()
    props.addProperty("Scalar", 1.5)
    props.setProperty("Scalar", 2)
    assert props.getProperty("Scalar") == 2.0
    assert isinstance(props.getProperty("Scalar"), float)

    props.addProperty("Count", 3)
    props.setProperty("Count", True)
    assert props.getProperty("Count") == 1
    assert isinstance(props.getProperty("Count"), int)


def test_type_mismatch_raises_value_error():
    props = PropertySet()
    props.addProperty("Scalar", 1.0)
    with pytest.raises(ValueError):
        props.setProperty("Scalar", [1, 2])

    props.addProperty("Vector", [1.0, 2.0])
    with pytest.raises(ValueError):
        props.setProperty("Vector", 5)


def test_enum_properties_accept_string_and_int():
    attrs = PropertyAttributes(enumNames=["Surface", "Wireframe", "Points"])
    props = PropertySet()
    props.addProperty("Surface Mode", 0, attributes=attrs)

    props.setProperty("Surface Mode", "Wireframe")
    assert props.getProperty("Surface Mode") == 1
    assert props.getPropertyEnumValue("Surface Mode") == "Wireframe"

    props.setProperty("Surface Mode", 2)
    assert props.getProperty("Surface Mode") == 2
    assert props.getPropertyEnumValue("Surface Mode") == "Points"

    with pytest.raises(ValueError):
        props.setProperty("Surface Mode", "Invalid")
