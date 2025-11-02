# VTK QVTKRenderWindowInteractor RecursionError Fix

## Problem

The `QVTKRenderWindowInteractor` class has a recursion bug that occurs during widget cleanup. When the widget is closed:

1. `closeEvent()` is called
2. It calls `Finalize()` which tries to access `self._RenderWindow`
3. Since `_RenderWindow` doesn't exist as a direct attribute, Python calls `__getattr__('_RenderWindow')`
4. `__getattr__` checks `hasattr(self._Iren, attr)` 
5. If `_Iren` is None or has been cleaned up, `hasattr` triggers `__getattr__` again
6. This creates infinite recursion: `RecursionError: maximum recursion depth exceeded`

## Solution

The fix involves three changes:

1. **Fix `__getattr__`**: Check if `_Iren` exists using `__dict__` (to avoid triggering `__getattr__` recursively) before trying to access it.

2. **Fix `Finalize()`**: Check if `_RenderWindow` exists using `__dict__` before trying to finalize it, and mark it as None after finalization to prevent double-finalization.

3. **Fix `closeEvent()`**: Check if `_RenderWindow` exists before calling `Finalize()`.

## Applying the Patch

Run the provided script:

```bash
python3 apply_vtk_fix.py
```

Or manually apply the changes shown in `QVTKRenderWindowInteractor_fix.patch`.

## Changes Made

### 1. `__getattr__` method (around line 412):
- Added check for `_Iren` existence using `__dict__` to prevent recursion
- Raises a clear AttributeError if `_Iren` is not initialized

### 2. `Finalize()` method (around line 426):
- Added check for `_RenderWindow` existence using `__dict__`
- Sets `_RenderWindow` to None after finalization to prevent double-finalization

### 3. `closeEvent()` method (around line 455):
- Added check before calling `Finalize()` to ensure `_RenderWindow` exists

## Verification

After applying the patch, all tests in `test_vtk_widget.py` should pass without recursion errors:

```bash
pytest tests/test_vtk_widget.py -v
```

## Files

- `apply_vtk_fix.py`: Script to automatically apply the patch
- `QVTKRenderWindowInteractor_fix.patch`: Unified diff patch file (for reference)
- `.venv/lib/python3.12/site-packages/vtkmodules/qt/QVTKRenderWindowInteractor.py.backup`: Backup of original file

