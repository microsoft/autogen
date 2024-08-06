# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "agnext"
copyright = "2024, Microsoft"
author = "Microsoft"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinxcontrib.apidoc",
    "myst_nb",
    "sphinx.ext.intersphinx",
    "IPython.sphinxext.ipython_console_highlighting",
]

apidoc_module_dir = "../../src/agnext"
apidoc_output_dir = "reference"
apidoc_template_dir = "_apidoc_templates"
apidoc_separate_modules = True
apidoc_extra_args = ["--no-toc"]
napoleon_custom_sections = [("Returns", "params_style")]
apidoc_excluded_paths = ["./worker/protos/"]

templates_path = []
exclude_patterns = ["reference/agnext.rst"]

autoclass_content = "init"

# TODO: incldue all notebooks excluding those requiring remote API access.
nb_execution_mode = "off"

# Guides and tutorials must succeed.
nb_execution_raise_on_error = True
nb_execution_timeout = 60

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_title = "AGNext"

html_theme = "furo"
html_static_path = ["_static"]

html_theme_options = {
    "source_repository": "https://github.com/microsoft/agnext",
    "source_branch": "main",
    "source_directory": "python/docs/src/",
}

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
}

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
