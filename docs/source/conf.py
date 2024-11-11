# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import liquid2

project = "Liquid2"
copyright = "2024, James Prior"  # noqa: A001
author = "James Prior"
release = liquid2.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.githubpages",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


autodoc_default_options = {
    "ignore-module-all": True,
}

myst_enable_extensions = ["colon_fence"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]

html_theme_options = {
    # "logo": {
    #     "image_light": "logo.png",
    #     "image_dark": "logo_dark.png",
    # },
    # https://pydata-sphinx-theme.readthedocs.io/en/stable/user_guide/header-links.html#fontawesome-icons
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/jg-rp/python-liquid2",
            "icon": "fa-brands fa-github",
        },
    ],
}

html_context = {
    "github_user": "jg-rp",
    "github_repo": "python-liquid2",
    "github_version": "main",
    "doc_path": "doc/source/",
    "default_mode": "light",
}
