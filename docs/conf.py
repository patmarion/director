project = "director"
copyright = "2025, Director Contributors"
author = "Director Contributors"
version = "2.0.0"
release = "2.0.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autosummary_generate = True

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_static_path = ["_static"]
html_title = "Director Documentation"
html_permalinks_icon = "#"
# html_logo = "_static/logo.png"


html_sidebars = {
    "**": [
        "sidebar/scroll-start.html",
        "sidebar/brand.html",
        "sidebar/search.html",
        "sidebar/navigation.html",
        "sidebar/links.html",
        "sidebar/scroll-end.html",
    ]
}
