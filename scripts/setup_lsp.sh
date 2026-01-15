#!/bin/bash
#
# CodeHero LSP Setup Script
# Installs Language Server Protocol servers for code intelligence
#
# Supported languages:
# - Python (pylsp)
# - JavaScript/TypeScript (typescript-language-server)
# - HTML/CSS/JSON (vscode-langservers-extracted)
# - PHP (intelephense)
# - Java (jdtls)
# - C#/.NET (omnisharp)
# - Kotlin (kotlin-language-server)
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   CodeHero LSP Setup Script${NC}"
echo -e "${BLUE}======================================${NC}"
echo

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    SUDO=""
else
    SUDO="sudo"
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function to install a package if not present
install_if_missing() {
    local cmd=$1
    local package=$2
    local install_cmd=$3

    if command_exists "$cmd"; then
        echo -e "${GREEN}[OK]${NC} $cmd is already installed"
        return 0
    else
        echo -e "${YELLOW}[INSTALLING]${NC} $package..."
        eval "$install_cmd"
        if command_exists "$cmd"; then
            echo -e "${GREEN}[OK]${NC} $package installed successfully"
            return 0
        else
            echo -e "${RED}[FAILED]${NC} Failed to install $package"
            return 1
        fi
    fi
}

# Ensure pip and npm are available
echo -e "${BLUE}Checking prerequisites...${NC}"
echo

if ! command_exists pip3; then
    echo -e "${YELLOW}Installing pip3...${NC}"
    $SUDO apt-get update
    $SUDO apt-get install -y python3-pip
fi

if ! command_exists npm; then
    echo -e "${YELLOW}Installing npm...${NC}"
    $SUDO apt-get update
    $SUDO apt-get install -y npm
    # Update npm to latest
    $SUDO npm install -g npm@latest
fi

if ! command_exists node; then
    echo -e "${YELLOW}Installing Node.js...${NC}"
    $SUDO apt-get update
    $SUDO apt-get install -y nodejs
fi

echo
echo -e "${BLUE}Installing Language Servers...${NC}"
echo

# ====================
# Python LSP Server
# ====================
echo -e "${BLUE}[1/7] Python Language Server (pylsp)${NC}"
install_if_missing "pylsp" "python-lsp-server" "pip3 install python-lsp-server"
echo

# ====================
# TypeScript/JavaScript Language Server
# ====================
echo -e "${BLUE}[2/7] TypeScript/JavaScript Language Server${NC}"
install_if_missing "typescript-language-server" "typescript-language-server" "$SUDO npm install -g typescript typescript-language-server"
echo

# ====================
# HTML/CSS/JSON Language Servers (VSCode extracted)
# ====================
echo -e "${BLUE}[3/7] HTML/CSS/JSON Language Servers${NC}"
install_if_missing "vscode-html-language-server" "vscode-langservers-extracted" "$SUDO npm install -g vscode-langservers-extracted"
echo

# ====================
# PHP Language Server (Intelephense)
# ====================
echo -e "${BLUE}[4/7] PHP Language Server (Intelephense)${NC}"
install_if_missing "intelephense" "intelephense" "$SUDO npm install -g intelephense"
echo

# ====================
# Java Language Server (jdtls)
# ====================
echo -e "${BLUE}[5/7] Java Language Server (jdtls)${NC}"
JDTLS_VERSION="1.31.0"
JDTLS_DIR="/opt/jdtls"
JDTLS_BIN="/usr/local/bin/jdtls"

if [ -f "$JDTLS_BIN" ] && [ -d "$JDTLS_DIR" ]; then
    echo -e "${GREEN}[OK]${NC} jdtls is already installed"
else
    echo -e "${YELLOW}[INSTALLING]${NC} Eclipse JDT Language Server..."

    # Check if Java is installed
    if ! command_exists java; then
        echo -e "${YELLOW}Installing Java JDK...${NC}"
        $SUDO apt-get update
        $SUDO apt-get install -y default-jdk
    fi

    # Download and extract jdtls
    $SUDO mkdir -p "$JDTLS_DIR"
    JDTLS_TAR="/tmp/jdtls.tar.gz"

    # Download from Eclipse
    curl -fsSL "https://download.eclipse.org/jdtls/milestones/${JDTLS_VERSION}/jdt-language-server-${JDTLS_VERSION}-202312211634.tar.gz" -o "$JDTLS_TAR" 2>/dev/null || \
    curl -fsSL "https://download.eclipse.org/jdtls/snapshots/jdt-language-server-latest.tar.gz" -o "$JDTLS_TAR" 2>/dev/null || \
    echo -e "${RED}[FAILED]${NC} Could not download jdtls. You may need to install it manually."

    if [ -f "$JDTLS_TAR" ]; then
        $SUDO tar -xzf "$JDTLS_TAR" -C "$JDTLS_DIR"
        rm -f "$JDTLS_TAR"

        # Create launcher script
        $SUDO tee "$JDTLS_BIN" > /dev/null << 'EOFSCRIPT'
#!/bin/bash
JDTLS_HOME="/opt/jdtls"
java \
    -Declipse.application=org.eclipse.jdt.ls.core.id1 \
    -Dosgi.bundles.defaultStartLevel=4 \
    -Declipse.product=org.eclipse.jdt.ls.core.product \
    -Dlog.level=ALL \
    -noverify \
    -Xmx1G \
    --add-modules=ALL-SYSTEM \
    --add-opens java.base/java.util=ALL-UNNAMED \
    --add-opens java.base/java.lang=ALL-UNNAMED \
    -jar $(find "$JDTLS_HOME/plugins" -name "org.eclipse.equinox.launcher_*.jar" | head -1) \
    -configuration "$JDTLS_HOME/config_linux" \
    -data "${1:-/tmp/jdtls-workspace}" \
    "$@"
EOFSCRIPT
        $SUDO chmod +x "$JDTLS_BIN"
        echo -e "${GREEN}[OK]${NC} jdtls installed successfully"
    fi
fi
echo

# ====================
# C#/.NET Language Server (OmniSharp)
# ====================
echo -e "${BLUE}[6/7] C#/.NET Language Server (OmniSharp)${NC}"
OMNISHARP_DIR="/opt/omnisharp"
OMNISHARP_BIN="/usr/local/bin/omnisharp"

if [ -f "$OMNISHARP_BIN" ]; then
    echo -e "${GREEN}[OK]${NC} omnisharp is already installed"
else
    echo -e "${YELLOW}[INSTALLING]${NC} OmniSharp Language Server..."

    # Detect architecture
    ARCH=$(uname -m)
    case $ARCH in
        x86_64) OMNISHARP_ARCH="linux-x64" ;;
        aarch64) OMNISHARP_ARCH="linux-arm64" ;;
        *) echo -e "${RED}[FAILED]${NC} Unsupported architecture: $ARCH"; OMNISHARP_ARCH="" ;;
    esac

    if [ -n "$OMNISHARP_ARCH" ]; then
        $SUDO mkdir -p "$OMNISHARP_DIR"
        OMNISHARP_VERSION="v1.39.11"
        OMNISHARP_URL="https://github.com/OmniSharp/omnisharp-roslyn/releases/download/${OMNISHARP_VERSION}/omnisharp-${OMNISHARP_ARCH}-net6.0.tar.gz"

        curl -fsSL "$OMNISHARP_URL" -o /tmp/omnisharp.tar.gz 2>/dev/null || \
        echo -e "${RED}[FAILED]${NC} Could not download OmniSharp. You may need to install it manually."

        if [ -f "/tmp/omnisharp.tar.gz" ]; then
            $SUDO tar -xzf /tmp/omnisharp.tar.gz -C "$OMNISHARP_DIR"
            rm -f /tmp/omnisharp.tar.gz

            # Create launcher script
            $SUDO tee "$OMNISHARP_BIN" > /dev/null << 'EOFSCRIPT'
#!/bin/bash
/opt/omnisharp/OmniSharp "$@"
EOFSCRIPT
            $SUDO chmod +x "$OMNISHARP_BIN"
            $SUDO chmod +x "$OMNISHARP_DIR/OmniSharp"
            echo -e "${GREEN}[OK]${NC} omnisharp installed successfully"
        fi
    fi
fi
echo

# ====================
# Kotlin Language Server
# ====================
echo -e "${BLUE}[7/7] Kotlin Language Server${NC}"
KOTLIN_LS_DIR="/opt/kotlin-language-server"
KOTLIN_LS_BIN="/usr/local/bin/kotlin-language-server"

if [ -f "$KOTLIN_LS_BIN" ]; then
    echo -e "${GREEN}[OK]${NC} kotlin-language-server is already installed"
else
    echo -e "${YELLOW}[INSTALLING]${NC} Kotlin Language Server..."

    # Check if Java is installed
    if ! command_exists java; then
        echo -e "${YELLOW}Installing Java JDK...${NC}"
        $SUDO apt-get update
        $SUDO apt-get install -y default-jdk
    fi

    $SUDO mkdir -p "$KOTLIN_LS_DIR"
    KOTLIN_LS_VERSION="1.3.9"
    KOTLIN_LS_URL="https://github.com/fwcd/kotlin-language-server/releases/download/${KOTLIN_LS_VERSION}/server.zip"

    curl -fsSL "$KOTLIN_LS_URL" -o /tmp/kotlin-ls.zip 2>/dev/null || \
    echo -e "${RED}[FAILED]${NC} Could not download Kotlin Language Server. You may need to install it manually."

    if [ -f "/tmp/kotlin-ls.zip" ]; then
        $SUDO unzip -q -o /tmp/kotlin-ls.zip -d "$KOTLIN_LS_DIR"
        rm -f /tmp/kotlin-ls.zip

        # Create symlink to bin
        if [ -f "$KOTLIN_LS_DIR/server/bin/kotlin-language-server" ]; then
            $SUDO ln -sf "$KOTLIN_LS_DIR/server/bin/kotlin-language-server" "$KOTLIN_LS_BIN"
            $SUDO chmod +x "$KOTLIN_LS_DIR/server/bin/kotlin-language-server"
            echo -e "${GREEN}[OK]${NC} kotlin-language-server installed successfully"
        fi
    fi
fi
echo

# ====================
# Summary
# ====================
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   Installation Summary${NC}"
echo -e "${BLUE}======================================${NC}"
echo

check_and_report() {
    local cmd=$1
    local name=$2
    if command_exists "$cmd"; then
        local version=$($cmd --version 2>/dev/null | head -1 || echo "installed")
        echo -e "${GREEN}[OK]${NC} $name: $version"
    else
        echo -e "${RED}[MISSING]${NC} $name"
    fi
}

check_and_report "pylsp" "Python LSP"
check_and_report "typescript-language-server" "TypeScript/JavaScript LSP"
check_and_report "vscode-html-language-server" "HTML LSP"
check_and_report "vscode-css-language-server" "CSS LSP"
check_and_report "vscode-json-language-server" "JSON LSP"
check_and_report "intelephense" "PHP LSP (Intelephense)"
check_and_report "jdtls" "Java LSP (jdtls)"
check_and_report "omnisharp" "C#/.NET LSP (OmniSharp)"
check_and_report "kotlin-language-server" "Kotlin LSP"

echo
echo -e "${GREEN}LSP setup complete!${NC}"
echo -e "Restart CodeHero services to apply changes:"
echo -e "  ${YELLOW}sudo systemctl restart codehero-web${NC}"
echo
