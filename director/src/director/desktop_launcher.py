"""Desktop launcher installation utilities for Linux."""

import sys
from pathlib import Path

import qtpy.QtGui as QtGui
import qtpy.QtWidgets as QtWidgets


def install_icon(
    icon: QtGui.QIcon,
    icon_name: str,
    size: int = 64,
    overwrite: bool = False,
) -> Path:
    """
    Install an icon to the user's local icon directory.

    Saves the icon as a PNG in ~/.local/share/icons/hicolor/{size}x{size}/apps/
    If the icon file already exists and overwrite is False, returns the existing path.

    Args:
        icon: QIcon to save
        icon_name: Base name for the icon file (without extension)
        size: Icon size in pixels (default: 64)
        overwrite: If False, skip if file already exists (default: False)

    Returns:
        Path to the icon file

    Raises:
        ValueError: If the icon is null and file doesn't already exist
        OSError: If file save fails
    """
    icons_dir = Path.home() / ".local" / "share" / "icons" / "hicolor" / f"{size}x{size}" / "apps"
    icon_path = icons_dir / f"{icon_name}.png"
    if icon_path.exists() and not overwrite:
        return icon_path

    if icon.isNull():
        raise ValueError("Icon is null. Cannot save icon.")

    icons_dir.mkdir(parents=True, exist_ok=True)
    pixmap = icon.pixmap(size, size)
    if not pixmap.save(str(icon_path), "PNG"):
        raise OSError(f"Failed to save icon to {icon_path}")

    return icon_path


def install_desktop_launcher(
    app_name: str,
    executable: str,
    icon_name: str,
    launcher_name: str,
    comment: str = "",
    categories: str = "Utility;",
    startup_wm_class: str = "Director_MainWindowApp",
    overwrite: bool = False,
) -> Path:
    """
    Install a desktop launcher (.desktop file) for an application.

    Creates a .desktop file in ~/.local/share/applications/
    If the file already exists and overwrite is False, returns the existing path.

    Args:
        app_name: Application name displayed in menus
        executable: Path to the executable
        icon_name: Icon name (should match an installed icon)
        launcher_name: Base name for the .desktop file (without extension)
        comment: Description shown in application menus
        categories: Semicolon-separated category list (default: "Utility;")
        startup_wm_class: WM_CLASS for window matching
        overwrite: If False, skip if file already exists (default: False)

    Returns:
        Path to the .desktop file

    Raises:
        OSError: If file operations fail
    """
    applications_dir = Path.home() / ".local" / "share" / "applications"
    desktop_path = applications_dir / f"{launcher_name}.desktop"
    if desktop_path.exists() and not overwrite:
        return desktop_path

    desktop_content = f"""[Desktop Entry]
Type=Application
Name={app_name}
Comment={comment}
Exec={executable}
Icon={icon_name}
Categories={categories}
Terminal=false
StartupWMClass={startup_wm_class}
"""

    applications_dir.mkdir(parents=True, exist_ok=True)
    desktop_path.write_text(desktop_content)
    return desktop_path


def install_desktop_launcher_from_window(
    main_window: QtWidgets.QMainWindow,
    launcher_name: str,
    icon_name: str,
    executable: str = "",
    comment: str = "",
    categories: str = "Utility;",
    startup_wm_class: str = "Director_MainWindowApp",
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """
    Install a desktop launcher by extracting info from a QMainWindow.

    Convenience wrapper that extracts the application name from the window title
    and the icon from the window icon.
    If files already exist and overwrite is False, returns the existing paths.

    Args:
        main_window: QMainWindow to extract app name and icon from
        launcher_name: Base name for the .desktop file (without extension)
        icon_name: Base name for the icon file (without extension)
        executable: Path to the executable (defaults to sys.argv[0] if empty)
        comment: Description shown in application menus
        categories: Semicolon-separated category list (default: "Utility;")
        startup_wm_class: WM_CLASS for window matching
        overwrite: If False, skip if files already exist (default: False)

    Returns:
        Tuple of (desktop_file_path, icon_file_path)

    Raises:
        ValueError: If the window has no icon set and icon file doesn't exist
        OSError: If file operations fail
    """
    app_name = main_window.windowTitle()
    icon = main_window.windowIcon()

    if not executable:
        executable = sys.argv[0]

    icon_path = install_icon(
        icon=icon,
        icon_name=icon_name,
        overwrite=overwrite,
    )

    desktop_path = install_desktop_launcher(
        app_name=app_name,
        executable=executable,
        icon_name=icon_name,
        launcher_name=launcher_name,
        comment=comment,
        categories=categories,
        startup_wm_class=startup_wm_class,
        overwrite=overwrite,
    )

    return desktop_path, icon_path
