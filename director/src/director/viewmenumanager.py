"""View menu manager for managing widgets in the View menu."""

from qtpy.QtCore import QObject, QEvent


class VisibilityEventFilter(QObject):
    """Event filter to sync menu checkbox with widget visibility."""

    def __init__(self, widget, action):
        super().__init__()
        self.widget = widget
        self.action = action

    def eventFilter(self, obj, event):
        """Filter show/hide events to sync checkbox state."""
        if obj == self.widget:
            if event.type() == QEvent.Show:
                self.action.setChecked(True)
            elif event.type() == QEvent.Hide:
                self.action.setChecked(False)
        return False  # Don't consume the event, let it propagate


class ViewMenuManager:
    """Simple manager for adding widgets to a View menu."""

    def __init__(self, menu):
        """
        Initialize the view menu manager.

        Args:
            menu: QMenu instance to manage
        """
        self.menu = menu
        self._filters = {}  # Store event filters to prevent garbage collection

    def addWidget(self, widget, title=None):
        """
        Add a widget action to the menu.

        Args:
            widget: QWidget or QDockWidget to add
            title: Optional title, defaults to widget.windowTitle() or widget.objectName()
        """
        if title is None:
            if hasattr(widget, "windowTitle"):
                title = widget.windowTitle()
            elif hasattr(widget, "objectName"):
                title = widget.objectName()
            else:
                title = "Widget"

        action = self.menu.addAction(title)

        # Connect toggle for dock widgets
        if hasattr(widget, "setVisible") and hasattr(widget, "isVisible"):
            action.setCheckable(True)
            action.setChecked(widget.isVisible())

            def toggle():
                widget.setVisible(not widget.isVisible())

            action.triggered.connect(toggle)

            # Install event filter to sync checkbox with visibility changes
            event_filter = VisibilityEventFilter(widget, action)
            widget.installEventFilter(event_filter)
            # Store filter to prevent garbage collection
            self._filters[widget] = event_filter

    def addSeparator(self):
        """Add a separator to the menu."""
        self.menu.addSeparator()
