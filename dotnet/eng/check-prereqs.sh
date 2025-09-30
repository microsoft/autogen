#!/usr/bin/env bash
set -euo pipefail

MISSING=()
INSTALL=false

if [[ "${1:-}" == "--install-missing" ]]; then
  INSTALL=true
fi

check_command() {
  local name=$1
  if ! command -v "$name" &>/dev/null; then
    printf "Missing: %-10s - not found in PATH\n" "$name"
    MISSING+=("$name")
  else
    printf "Found:   %-10s\n" "$name"
  fi
}

install_tool() {
  local tool=$1
  echo "Installing $tool..."
  case "$tool" in
    python3)
      if command -v brew &>/dev/null; then
        brew install python
      elif command -v apt &>/dev/null; then
        sudo apt update && sudo apt install -y python3
      elif command -v dnf &>/dev/null; then
        sudo dnf install -y python3
      else
        echo "Unsupported package manager. Please install $tool manually."
        return 1
      fi
      ;;
    uv)
      curl -Ls https://astral.sh/uv/install.sh | sh
      ;;
    *)
      echo "No install method defined for: $tool"
      return 1
      ;;
  esac
}

echo "Checking for required tools..."
check_command python3
check_command uv

if [ ${#MISSING[@]} -ne 0 ]; then
  echo ""
  echo "Missing tools detected: ${MISSING[*]}"

  if [ "$INSTALL" = true ]; then
    for tool in "${MISSING[@]}"; do
      install_tool "$tool"
    done
    echo "All missing tools have been installed."
  else
    echo "Some required tools are missing. Use '--install-missing' to install them automatically."
      echo ""
      echo "For manual setup instructions, see: "
      echo "https://github.com/microsoft/autogen/blob/main/python/README.md#setup"
    exit 1
  fi
else
  echo "All required tools are installed."
fi
