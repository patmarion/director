"""Tests for componentfactory module."""

import pytest
from director.componentgraph import ComponentFactory, ComponentGraph
from director.fieldcontainer import FieldContainer


class TestComponentGraph:
    """Test ComponentGraph functionality."""

    def test_add_component(self):
        graph = ComponentGraph()
        graph.addComponent("A", [])
        graph.addComponent("B", ["A"])
        graph.addComponent("C", ["A", "B"])

        assert "A" in graph.getComponentNames()
        assert "B" in graph.getComponentNames()
        assert "C" in graph.getComponentNames()

    def test_get_component_dependencies(self):
        graph = ComponentGraph()
        graph.addComponent("A", [])
        graph.addComponent("B", ["A"])
        graph.addComponent("C", ["A", "B"])

        deps_A = graph.getComponentDependencies("A")
        assert deps_A == []

        deps_B = graph.getComponentDependencies("B")
        assert "A" in deps_B
        assert len(deps_B) == 1

        deps_C = graph.getComponentDependencies("C")
        assert "A" in deps_C
        assert "B" in deps_C
        assert len(deps_C) == 2


class TestComponentFactory:
    """Test ComponentFactory functionality."""

    def test_factory_registration(self):
        class TestFactory:
            def getComponents(self):
                components = {
                    "ComponentA": [],
                    "ComponentB": ["ComponentA"],
                }
                disabledComponents = []
                return components, disabledComponents

            def initComponentA(self, fields):
                return FieldContainer(valueA=42)

            def initComponentB(self, fields):
                return FieldContainer(valueB=fields.valueA + 1)

        factory = ComponentFactory()
        factory.register(TestFactory)

        # Check that components were registered
        assert "ComponentA" in factory.componentGraph.getComponentNames()
        assert "ComponentB" in factory.componentGraph.getComponentNames()

    def test_factory_construction(self):
        class TestFactory:
            def getComponents(self):
                components = {
                    "ComponentA": [],
                    "ComponentB": ["ComponentA"],
                }
                disabledComponents = []
                return components, disabledComponents

            def initComponentA(self, fields):
                return FieldContainer(valueA=42)

            def initComponentB(self, fields):
                return FieldContainer(valueB=fields.valueA + 1)

        factory = ComponentFactory()
        factory.register(TestFactory)

        # Construct with default options
        fields = factory.construct()

        # Check that both components were initialized
        assert hasattr(fields, "valueA")
        assert hasattr(fields, "valueB")
        assert fields.valueA == 42
        assert fields.valueB == 43

    def test_factory_disabled_components(self):
        class TestFactory:
            def getComponents(self):
                components = {
                    "ComponentA": [],
                    "ComponentB": ["ComponentA"],
                }
                disabledComponents = ["ComponentB"]
                return components, disabledComponents

            def initComponentA(self, fields):
                return FieldContainer(valueA=42)

            def initComponentB(self, fields):
                return FieldContainer(valueB=fields.valueA + 1)

        factory = ComponentFactory()
        factory.register(TestFactory)

        # Construct with default options (ComponentB should be disabled)
        fields = factory.construct()

        # Check that only ComponentA was initialized
        assert hasattr(fields, "valueA")
        assert fields.valueA == 42
        assert not hasattr(fields, "valueB")

    def test_factory_custom_kwargs(self):
        class TestFactory:
            def getComponents(self):
                components = {
                    "ComponentA": [],
                }
                disabledComponents = []
                return components, disabledComponents

            def initComponentA(self, fields):
                return FieldContainer(valueA=fields.custom_value * 2)

        factory = ComponentFactory()
        factory.register(TestFactory)

        # Construct with custom kwargs
        fields = factory.construct(custom_value=21)

        assert fields.valueA == 42

    def test_factory_missing_init_function(self):
        class TestFactory:
            def getComponents(self):
                components = {
                    "ComponentA": [],
                }
                disabledComponents = []
                return components, disabledComponents

            # Missing initComponentA method

        factory = ComponentFactory()

        with pytest.raises(Exception, match="Missing init function"):
            factory.register(TestFactory)

    def test_factory_duplicate_component(self):
        class Factory1:
            def getComponents(self):
                components = {"ComponentA": []}
                return components, []

            def initComponentA(self, fields):
                return FieldContainer()

        class Factory2:
            def getComponents(self):
                components = {"ComponentA": []}  # Duplicate!
                return components, []

            def initComponentA(self, fields):
                return FieldContainer()

        factory = ComponentFactory()
        factory.register(Factory1)

        with pytest.raises(Exception, match="has already been registered"):
            factory.register(Factory2)

    def test_factory_dependency_ordering(self):
        """Test that components are initialized in dependency order."""
        init_order = []

        class TestFactory:
            def getComponents(self):
                components = {
                    "ComponentA": [],
                    "ComponentB": ["ComponentA"],
                    "ComponentC": ["ComponentB"],
                }
                disabledComponents = []
                return components, disabledComponents

            def initComponentA(self, fields):
                init_order.append("A")
                return FieldContainer(valueA=1)

            def initComponentB(self, fields):
                init_order.append("B")
                # Verify dependency was initialized first
                assert "A" in init_order
                return FieldContainer(valueB=fields.valueA + 1)

            def initComponentC(self, fields):
                init_order.append("C")
                # Verify dependency was initialized first
                assert "B" in init_order
                return FieldContainer(valueC=fields.valueB + 1)

        factory = ComponentFactory()
        factory.register(TestFactory)

        fields = factory.construct()

        # Verify initialization order
        assert init_order == ["A", "B", "C"]
        assert fields.valueA == 1
        assert fields.valueB == 2
        assert fields.valueC == 3

    def test_factory_set_dependent_options(self):
        class TestFactory:
            def getComponents(self):
                components = {
                    "ComponentA": [],
                    "ComponentB": ["ComponentA"],
                }
                disabledComponents = []
                return components, disabledComponents

            def initComponentA(self, fields):
                return FieldContainer()

            def initComponentB(self, fields):
                return FieldContainer()

        factory = ComponentFactory()
        factory.register(TestFactory)

        # Get options and disable ComponentA
        options = factory.getDefaultOptions()
        options.useComponentA = False

        # But enabling ComponentB should also enable ComponentA (dependency)
        options = factory.getDefaultOptions()
        factory.setDependentOptions(options, useComponentB=True)
        assert options.useComponentA == True
        assert options.useComponentB == True
