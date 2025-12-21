#!/usr/bin/env python3
"""
Apply fix to QVTKRenderWindowInteractor.py to prevent RecursionError during cleanup.

This script patches the VTK file to fix the recursion issue that occurs when
the widget is closed and _Iren or _RenderWindow have been cleaned up.
"""

import inspect
import os
import sys


def apply_fix():
    """Apply the fix to QVTKRenderWindowInteractor.py"""

    # Find the VTK file
    try:
        import vtkmodules.qt.QVTKRenderWindowInteractor as qvtk

        vtk_file = inspect.getfile(qvtk)
    except ImportError:
        print("Error: Could not import vtkmodules.qt.QVTKRenderWindowInteractor")
        return False

    # Create backup
    backup_file = vtk_file + ".backup"
    if not os.path.exists(backup_file):
        print(f"Creating backup at: {backup_file}")
        with open(vtk_file, "r") as f:
            content = f.read()
        with open(backup_file, "w") as f:
            f.write(content)
    else:
        print(f"Backup already exists at: {backup_file}")

    # Read the file
    print(f"Reading: {vtk_file}")
    with open(vtk_file, "r") as f:
        content = f.read()

    # Check if already patched
    if "_Iren is not initialized" in content:
        print("File appears to already be patched!")
        return True

    # Fix 1: Update __getattr__ method - must use __dict__ check to avoid recursion

    content = content.replace(
        '    def __getattr__(self, attr):\n        """Makes the object behave like a vtkGenericRenderWindowInteractor"""\n        if attr == \'__vtk__\':',
        '''    def __getattr__(self, attr):
        """Makes the object behave like a vtkGenericRenderWindowInteractor"""
        # Check if _Iren exists to prevent recursion when it's None during cleanup
        # Use __dict__ to avoid triggering __getattr__ recursively
        if '_Iren' not in self.__dict__ or self.__dict__.get('_Iren') is None:
            raise AttributeError(self.__class__.__name__ +
                  " has no attribute named " + attr + " (_Iren is not initialized)")
        if attr == '__vtk__':''',
    )

    # Fix 2: Update Finalize method
    old_finalize = """    def Finalize(self):
        \'\'\'
        Call internal cleanup method on VTK objects
        \'\'\'
        self._RenderWindow.Finalize()"""

    new_finalize = """    def Finalize(self):
        \'\'\'
        Call internal cleanup method on VTK objects
        \'\'\'
        # Check if _RenderWindow exists before trying to finalize it
        # This prevents recursion errors during cleanup when _RenderWindow
        # might have already been cleaned up
        # Use __dict__ to avoid triggering __getattr__ recursively
        if '_RenderWindow' in self.__dict__ and self.__dict__.get('_RenderWindow') is not None:
            self.__dict__['_RenderWindow'].Finalize()
            # Mark as finalized to prevent double-finalization
            self.__dict__['_RenderWindow'] = None"""

    content = content.replace(old_finalize, new_finalize)

    # Fix 3: Update closeEvent method
    old_close = """    def closeEvent(self, evt):
        self.Finalize()"""

    new_close = """    def closeEvent(self, evt):
        # Only finalize if not already finalized and if objects still exist
        # Use __dict__ to avoid triggering __getattr__ recursively
        if '_RenderWindow' in self.__dict__ and self.__dict__.get('_RenderWindow') is not None:
            self.Finalize()"""

    content = content.replace(old_close, new_close)

    # Write the patched file
    print(f"Writing patched file: {vtk_file}")
    with open(vtk_file, "w") as f:
        f.write(content)

    print("Patch applied successfully!")
    return True


if __name__ == "__main__":
    success = apply_fix()
    sys.exit(0 if success else 1)
