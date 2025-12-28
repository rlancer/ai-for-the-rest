#!/bin/bash
# Setup script for new user environment (macOS)
# Bootstrap: installs Homebrew and packages, then hands off to TypeScript

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_PATH="$REPO_ROOT/config/config.json"

# Check for config file
if [ ! -f "$CONFIG_PATH" ]; then
    echo "ERROR: config.json not found at $CONFIG_PATH"
    exit 1
fi

# Check for jq (needed to parse JSON in bootstrap phase)
if ! command -v jq &> /dev/null; then
    echo "Installing jq for JSON parsing..."
    if command -v brew &> /dev/null; then
        brew install jq
    else
        echo "ERROR: jq is required but not installed. Please install Homebrew first."
        exit 1
    fi
fi

echo "Setting up your development environment..."

# Install Homebrew (if not already installed)
echo ""
echo "Installing Homebrew..."
if command -v brew &> /dev/null; then
    echo "  Homebrew already installed"
else
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add Homebrew to PATH for Apple Silicon Macs
    if [ -f "/opt/homebrew/bin/brew" ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
fi

# Add required taps from config
echo ""
echo "Adding Homebrew taps..."
for tap in $(jq -r '.buckets.brew[]' "$CONFIG_PATH"); do
    if brew tap | grep -q "^$tap$"; then
        echo "  $tap already added"
    else
        echo "  Adding $tap..."
        brew tap "$tap"
    fi
done

# Install common packages
echo ""
echo "Installing common packages..."
for pkg in $(jq -r '.packages.common.brew[]' "$CONFIG_PATH"); do
    if brew list "$pkg" &> /dev/null; then
        echo "  $pkg already installed"
    else
        echo "  Installing $pkg..."
        brew install "$pkg"
    fi
done

# Install macOS-specific packages (includes bun)
echo ""
echo "Installing macOS packages..."
for pkg in $(jq -r '.packages.macos.brew // [] | .[]' "$CONFIG_PATH"); do
    if brew list "$pkg" &> /dev/null; then
        echo "  $pkg already installed"
    else
        echo "  Installing $pkg..."
        brew install "$pkg"
    fi
done

# Install fonts (casks)
echo ""
echo "Installing fonts..."
for font in $(jq -r '.packages.fonts.brew_cask[]' "$CONFIG_PATH"); do
    if brew list --cask "$font" &> /dev/null; then
        echo "  $font already installed"
    else
        echo "  Installing $font..."
        brew install --cask "$font"
    fi
done

# Show bootstrap summary
echo ""
echo "=== Bootstrap Summary ==="
echo ""
echo "Homebrew packages:"
brew list --formula | sed 's/^/  /'

# Hand off to TypeScript for the rest of setup
echo ""
echo "=== Continuing with bun... ==="

SETUP_TS_PATH="$SCRIPT_DIR/setup.ts"

if [ -f "$SETUP_TS_PATH" ]; then
    bun run "$SETUP_TS_PATH"
else
    echo "ERROR: setup.ts not found at $SETUP_TS_PATH"
    exit 1
fi
