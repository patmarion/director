"""Tests for fieldcontainer module."""

import pytest
from director.fieldcontainer import FieldContainer


def test_field_container_creation():
    """Test creating a FieldContainer."""
    container = FieldContainer(x=1, y=2, z=3)
    
    assert container.x == 1
    assert container.y == 2
    assert container.z == 3


def test_field_container_getitem():
    """Test accessing fields via __getitem__."""
    container = FieldContainer(x=1, y=2)
    
    assert container['x'] == 1
    assert container['y'] == 2


def test_field_container_setitem():
    """Test setting fields via __setitem__."""
    container = FieldContainer(x=1, y=2)
    
    container['x'] = 10
    assert container.x == 10


def test_field_container_len():
    """Test getting length of FieldContainer."""
    container = FieldContainer(x=1, y=2, z=3)
    
    assert len(container) == 3


def test_field_container_contains():
    """Test checking if field exists."""
    container = FieldContainer(x=1, y=2)
    
    assert 'x' in container
    assert 'y' in container
    assert 'z' not in container


def test_field_container_iter():
    """Test iterating over FieldContainer."""
    container = FieldContainer(x=1, y=2, z=3)
    
    fields = dict(container)
    
    assert 'x' in fields
    assert 'y' in fields
    assert 'z' in fields
    assert fields['x'] == 1


def test_field_container_setattr_existing():
    """Test setting existing field."""
    container = FieldContainer(x=1)
    
    container.x = 10
    assert container.x == 10


def test_field_container_setattr_new():
    """Test that setting new field raises AttributeError."""
    container = FieldContainer(x=1)
    
    with pytest.raises(AttributeError):
        container.new_field = 10


def test_field_container_delattr():
    """Test deleting a field."""
    container = FieldContainer(x=1, y=2)
    
    del container.x
    
    assert 'x' not in container
    assert 'y' in container


def test_field_container_repr():
    """Test string representation."""
    container = FieldContainer(x=1, y=2)
    
    repr_str = repr(container)
    assert 'FieldContainer' in repr_str
    assert 'x' in repr_str
    assert 'y' in repr_str

