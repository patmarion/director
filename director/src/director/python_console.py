"""Python console widget for Director applications."""

import os
import sys
import vtk

try:
    from qtconsole.rich_jupyter_widget import RichJupyterWidget
    from qtconsole.inprocess import QtInProcessKernelManager
    QTCONSOLE_AVAILABLE = True
except ImportError:
    QTCONSOLE_AVAILABLE = False
    RichJupyterWidget = None
    QtInProcessKernelManager = None


class PythonConsoleWidget:
    """Manages a Python console widget with Jupyter kernel."""
    
    def __init__(self, namespace=None):
        """
        Create a Python console widget.
        
        Args:
            namespace: Dictionary of variables to push into the console's namespace.
                      If None, provides a minimal namespace with vtk and sys.
        """
        if not QTCONSOLE_AVAILABLE:
            raise RuntimeError("Python console not available. Please install qtconsole.")
        
        # Suppress warning about frozen modules interferring with breakpoints.
        os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'

        # Create the console widget
        self.console_widget = RichJupyterWidget()
        self.console_widget.setWindowTitle('Python Console')
        
        # Initialize the in-process kernel
        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel()
        kernel = self.kernel_manager.kernel
        kernel.gui = 'qt'
        
        # Start kernel client
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
        
        # Connect console to kernel
        self.console_widget.kernel_manager = self.kernel_manager
        self.console_widget.kernel_client = self.kernel_client
        self.console_widget.set_default_style()
        
        # Set up namespace with access to application objects
        default_namespace = {
            'vtk': vtk,
            'sys': sys,
        }
        
        if namespace:
            default_namespace.update(namespace)
        
        kernel.shell.push(default_namespace)
        self._kernel = kernel  # Store kernel reference for later namespace updates
    
    def push_variables(self, variables):
        """
        Add variables to the console's namespace.
        
        Args:
            variables: Dictionary of variable names and values to push into the namespace.
        """
        if hasattr(self, '_kernel') and self._kernel:
            self._kernel.shell.push(variables)
    
    def get_widget(self):
        """Get the console widget."""
        return self.console_widget
    
    def shutdown(self):
        """Shutdown the kernel and clean up resources."""
        try:
            if hasattr(self, 'kernel_client') and self.kernel_client:
                self.kernel_client.stop_channels()
            if hasattr(self, 'kernel_manager') and self.kernel_manager:
                self.kernel_manager.shutdown_kernel()
        except:
            pass  # Ignore errors during cleanup

