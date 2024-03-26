#!/bin/bash
#
# This script generates documentation using pydoc-markdown and renders the website using Quarto.
#

missing_deps=false

#
# Check for missing dependencies, report them, and exit when building the
# website is likely to fail.
#
for dependency in node pydoc-markdown quarto python yarn npm
do
    if ! command -v "$dependency" &> /dev/null
    then
        echo "Command '$dependency' not found."
        missing_deps=true
    fi
done

if [ "$missing_deps" = true ]
then
    echo -e "\nSome of the dependencies are missing."
    echo "Please install them to build the website."
    exit 1
fi

# Generate documentation using pydoc-markdown
pydoc-markdown

# Process notebooks using a Python script
python ./process_notebooks.py render

# Start the website using yarn
yarn start
