set -e

# Current script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [[ "$VIRTUAL_ENV" == "" ]]
then
    echo "Virtual environment is not activated"
    exit 1
fi

cd $DIR

echo "--- Running ruff format ---"
ruff format
echo "--- Running ruff check ---"
ruff check
echo "--- Running pyright ---"
pyright
echo "--- Running mypy ---"
mypy
