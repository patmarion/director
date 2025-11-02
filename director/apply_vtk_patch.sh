#!/bin/bash
# Script to apply the VTK patch to QVTKRenderWindowInteractor.py
# This fixes the RecursionError that occurs during widget cleanup

VTK_FILE="$(python3 -c 'import vtkmodules.qt.QVTKRenderWindowInteractor as qvtk; import inspect; print(inspect.getfile(qvtk))' 2>/dev/null)"

if [ -z "$VTK_FILE" ]; then
    echo "Error: Could not locate QVTKRenderWindowInteractor.py"
    exit 1
fi

echo "Found VTK file: $VTK_FILE"
echo "Creating backup at ${VTK_FILE}.backup"

cp "$VTK_FILE" "${VTK_FILE}.backup"

# Apply the fixes directly using Python
python3 << 'PYTHON_EOF'
import re

vtk_file = """$(python3 -c 'import vtkmodules.qt.QVTKRenderWindowInteractor as qvtk; import inspect; print(inspect.getfile(qvtk))' 2>/dev/null)"""

with open(vtk_file, 'r') as f:
    content = f.read()

# Fix 1: Update __getattr__ to check for _Iren existence
old_getattr = r'    def __getattr__\(self, attr\):\s*"""Makes the object behave like a vtkGenericRenderWindowInteractor"""\s*if attr == \'__vtk__\':'
new_getattr = '''    def __getattr__(self, attr):
        """Makes the object behave like a vtkGenericRenderWindowInteractor"""
        # Check if _Iren exists to prevent recursion when it's None during cleanup
        if not hasattr(self, '_Iren') or self._Iren is None:
            raise AttributeError(self.__class__.__name__ +
                  " has no attribute named " + attr + " (_Iren is not initialized)")
        if attr == '__vtk__':'''

content = re.sub(old_getattr, new_getattr, content)

# Fix 2: Update Finalize to check for _RenderWindow existence
old_finalize = r'    def Finalize\(self\):\s*\'\'\'\s*Call internal cleanup method on VTK objects\s*\'\'\'\s*self\._RenderWindow\.Finalize\(\)'
new_finalize = '''    def Finalize(self):
        \'\'\'
        Call internal cleanup method on VTK objects
        \'\'\'
        # Check if _RenderWindow exists before trying to finalize it
        # This prevents recursion errors during cleanup when _RenderWindow
        # might have already been cleaned up
        if hasattr(self, '_RenderWindow') and self._RenderWindow is not None:
            self._RenderWindow.Finalize()
            # Mark as finalized to prevent double-finalization
            self._RenderWindow = None'''

content = re.sub(old_finalize, new_finalize, content, flags=re.DOTALL)

# Fix 3: Update closeEvent to check before finalizing
old_close = r'    def closeEvent\(self, evt\):\s*self\.Finalize\(\)'
new_close = '''    def closeEvent(self, evt):
        # Only finalize if not already finalized and if objects still exist
        if hasattr(self, '_RenderWindow') and self._RenderWindow is not None:
            self.Finalize()'''

content = re.sub(old_close, new_close, content)

with open(vtk_file, 'w') as f:
    f.write(content)

print("Patch applied successfully!")
print("Backup saved at: {}.backup".format(vtk_file))

PYTHON_EOF

