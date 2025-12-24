#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DOCS_DIR = ROOT_DIR / "docs"
BUILD_DIR = DOCS_DIR / "_build"
GENERATED_DIR = DOCS_DIR / "generated"
SOURCE_DIR = ROOT_DIR / "src/director"


def run_command(cmd, cwd=None):
    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=cwd)


def clean():
    print("Cleaning build artifacts...")
    for dir in [BUILD_DIR, GENERATED_DIR]:
        if dir.exists():
            print(f"Removing {dir}...")
            shutil.rmtree(dir)

    print("Clean complete.")


def generate_api_rst():
    print("Generating api.rst...")
    modules = []

    # Walk through the director package
    for path in sorted(SOURCE_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        modules.append(f"director.{path.stem}")

    # Walk through thirdparty
    thirdparty_dir = SOURCE_DIR / "thirdparty"
    if thirdparty_dir.exists():
        for path in sorted(thirdparty_dir.glob("*.py")):
            if path.name == "__init__.py":
                continue
            modules.append(f"director.thirdparty.{path.stem}")

    content = [
        "API Reference",
        "=============",
        "",
        ".. autosummary::",
        "   :toctree: .",
        "   :template: custom-module-template.rst",
        "   :recursive:",
        "",
    ]

    for module in sorted(modules):
        content.append(f"   {module}")

    content.append("")

    # Ensure generated directory exists
    GENERATED_DIR.mkdir(exist_ok=True)

    with open(GENERATED_DIR / "api.rst", "w") as f:
        f.write("\n".join(content))

    print(f"Generated {GENERATED_DIR / 'api.rst'} with found modules.")


def build():
    generate_api_rst()

    print("Building HTML docs...")
    run_command(["sphinx-build", "-b", "html", str(DOCS_DIR), str(BUILD_DIR / "html")])
    print(f"Build complete. Docs are in {BUILD_DIR / 'html'}")


def view():
    index_path = BUILD_DIR / "html" / "index.html"
    if not index_path.exists():
        print("Docs not found. Please run 'build' first.")
        return

    print(f"Opening {index_path}...")
    webbrowser.open(f"file://{index_path.absolute()}")


def main():
    parser = argparse.ArgumentParser(description="Manage documentation")
    parser.add_argument("action", choices=["build", "clean", "view"], help="Action to perform")

    args = parser.parse_args()

    if args.action == "clean":
        clean()
    elif args.action == "build":
        build()
    elif args.action == "view":
        view()


if __name__ == "__main__":
    main()
