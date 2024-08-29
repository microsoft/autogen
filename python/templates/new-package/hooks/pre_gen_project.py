import re
import sys
from packaging import version

MODULE_REGEX = r'^[a-zA-Z][\-a-zA-Z0-9]+$'

package_name = '{{ cookiecutter.package_name }}'

at_least_one_error = False
if not re.match(MODULE_REGEX, package_name):
    print(f'ERROR: "{package_name}" must use kebab case')
    at_least_one_error = True

packaging_version = '{{ cookiecutter.version }}'

# Check version format using version.VERSION_PATTERN
if not re.match(version.VERSION_PATTERN, packaging_version, re.VERBOSE | re.IGNORECASE):
    print(f'ERROR: "{packaging_version}" is not a valid version string')
    at_least_one_error = True

if at_least_one_error:
    sys.exit(1)
