"""Reusable MainWindow class for Director 2.0 applications."""

import sys
import signal
import vtk
from qtpy.QtWidgets import QApplication, QMainWindow, QDockWidget, QTreeWidget
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QKeySequence

from director.vtk_widget import VTKWidget
from director.objectmodel import ObjectModelTree
import director.objectmodel as om
import director.applogic as applogic

try:
    from qtconsole.rich_jupyter_widget import RichJupyterWidget
    from qtconsole.inprocess import QtInProcessKernelManager
    QTCONSOLE_AVAILABLE = True
except ImportError:
    QTCONSOLE_AVAILABLE = False


class DummyPropertiesPanel:
    """Dummy properties panel for examples."""
    
    def clear(self):
        """Clear the panel."""
        pass
    
    def setBrowserModeToWidget(self):
        """Set browser mode to widget."""
        pass


class MainWindow(QMainWindow):
    """Main application window with VTK widget, object model, and optional Python console."""
    
    def __init__(self, window_title="Director 2.0", show_python_console=False):
        super().__init__()
        self.setWindowTitle(window_title)
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget with VTK
        self.vtk_widget = VTKWidget(self)
        self.setCentralWidget(self.vtk_widget)
        
        # Set as current render view for applogic
        applogic.setCurrentRenderView(self.vtk_widget)
        
        # Create menu bar
        self._setup_menu_bar()
        
        # Create object model dock widget (must be before console setup)
        self._setup_object_model()
        
        # Create Python console dock widget (initially hidden unless requested)
        self._python_console_dock = None
        if QTCONSOLE_AVAILABLE:
            self._setup_python_console()
            if show_python_console:
                self._toggle_python_console()
    
    def _setup_menu_bar(self):
        """Setup the menu bar."""
        menubar = self.menuBar()
        
        # Create File menu
        file_menu = menubar.addMenu("File")
        
        # Add Quit action
        quit_action = file_menu.addAction("Quit")
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.quit_application)
        
        # Create Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        # Add Python Console action
        python_console_action = tools_menu.addAction("Python Console")
        python_console_action.setShortcut(QKeySequence(Qt.Key_F8))
        python_console_action.triggered.connect(self._toggle_python_console)
    
    def quit_application(self):
        """Quit the application."""
        QApplication.instance().quit()
    
    def _setup_object_model(self):
        """Setup the object model as a dock widget."""
        # Create dock widget for object model
        dock = QDockWidget("Object Model", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # Create tree widget
        tree_widget = QTreeWidget()
        
        # Initialize the global object model (required for om.addToObjectModel to work)
        properties_panel = DummyPropertiesPanel()
        om.init(tree_widget, properties_panel)
        
        # Get the global object model instance
        self.object_model = om.getDefaultObjectModel()
        
        # Set tree widget as the dock widget's widget
        dock.setWidget(tree_widget)
        
        # Add dock widget to the left side
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        
        # Initialize grid now that object model is ready
        if hasattr(self, 'vtk_widget') and self.vtk_widget:
            self.vtk_widget.initializeGrid()
    
    def _setup_python_console(self):
        """Setup the Python console as a dock widget."""
        # Create dock widget for Python console
        dock = QDockWidget("Python Console", self)
        dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        
        # Create the console widget
        console_widget = RichJupyterWidget()
        
        # Initialize the in-process kernel
        kernel_manager = QtInProcessKernelManager()
        kernel_manager.start_kernel()
        kernel = kernel_manager.kernel
        kernel.gui = 'qt'
        
        # Start kernel client
        kernel_client = kernel_manager.client()
        kernel_client.start_channels()
        
        # Connect console to kernel
        console_widget.kernel_manager = kernel_manager
        console_widget.kernel_client = kernel_client
        console_widget.set_default_style()
        
        # Set up namespace with access to application objects
        kernel.shell.push({
            'app': self,
            'vtk_widget': self.vtk_widget,
            'object_model': self.object_model,
            'vtk': vtk,
            'sys': sys,
        })
        
        # Set console widget as dock widget's widget
        dock.setWidget(console_widget)
        
        # Store reference to dock
        self._python_console_dock = dock
        
        # Initially hide the console
        dock.hide()
    
    def _toggle_python_console(self):
        """Toggle the Python console dock widget visibility."""
        if self._python_console_dock is None:
            if QTCONSOLE_AVAILABLE:
                self._setup_python_console()
            else:
                print("Python console not available. Please install qtconsole.")
                return
        
        if self._python_console_dock.isVisible():
            self._python_console_dock.hide()
        else:
            self._python_console_dock.show()
            self.addDockWidget(Qt.BottomDockWidgetArea, self._python_console_dock)


def _setup_signal_handlers(app):
    """Setup signal handlers for graceful shutdown on Ctrl+C."""
    def signal_handler(signum, frame):
        """Handle SIGINT (Ctrl+C) by quitting the Qt application."""
        # Use QTimer.singleShot to ensure quit() is called from the Qt event loop
        print("Caught interrupt signal, quitting application...")
        QTimer.singleShot(0, app.quit)
    
    # Register signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Install custom exception hook to catch KeyboardInterrupt
    original_excepthook = sys.excepthook
    
    def exception_hook(exc_type, exc_value, exc_traceback):
        """Handle KeyboardInterrupt exceptions by quitting the application."""
        if exc_type is KeyboardInterrupt:
            # KeyboardInterrupt should quit the application gracefully
            QTimer.singleShot(0, app.quit)
        else:
            # For other exceptions, use the original exception handler
            original_excepthook(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = exception_hook


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Director 2.0")
    app.setApplicationVersion("2.0.0")
    
    # Setup signal handlers for Ctrl+C
    _setup_signal_handlers(app)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

