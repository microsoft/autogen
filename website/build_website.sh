#
# This script generates documentation using pydoc-markdown and renders the website using Quarto.
#
# Usage: bash build_website.sh
#

# Generate documentation using pydoc-markdown
pydoc-markdown

# Render the website using Quarto
quarto render ./docs

# Process notebooks using a Python script
python ./process_notebooks.py

# Start the website using yarn
yarn start
