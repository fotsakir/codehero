# CodeHero LSP Setup Guide

The Monaco Editor in CodeHero supports Language Server Protocol (LSP) for intelligent code features like autocomplete, hover documentation, go-to-definition, and real-time error checking.

## Quick Setup

Run the automated setup script:

```bash
sudo /opt/codehero/scripts/setup_lsp.sh
```

Then restart the web service:

```bash
sudo systemctl restart codehero-web
```

## Supported Languages

| Language | LSP Server | Install Command |
|----------|-----------|-----------------|
| Python | pylsp | `pip3 install python-lsp-server` |
| JavaScript | typescript-language-server | `npm install -g typescript typescript-language-server` |
| TypeScript | typescript-language-server | `npm install -g typescript typescript-language-server` |
| HTML | vscode-html-language-server | `npm install -g vscode-langservers-extracted` |
| CSS/SCSS/LESS | vscode-css-language-server | `npm install -g vscode-langservers-extracted` |
| JSON | vscode-json-language-server | `npm install -g vscode-langservers-extracted` |
| PHP | intelephense | `npm install -g intelephense` |
| Java | jdtls | See [Java Setup](#java-jdtls) |
| C# / .NET | omnisharp | See [C# Setup](#c-omnisharp) |
| Kotlin | kotlin-language-server | See [Kotlin Setup](#kotlin) |

## Manual Installation

### Prerequisites

```bash
# Install Node.js and npm
sudo apt-get update
sudo apt-get install -y nodejs npm python3-pip

# Update npm
sudo npm install -g npm@latest
```

### Python (pylsp)

```bash
pip3 install python-lsp-server
```

### JavaScript / TypeScript

```bash
sudo npm install -g typescript typescript-language-server
```

### HTML / CSS / JSON (VSCode servers)

```bash
sudo npm install -g vscode-langservers-extracted
```

This installs:
- `vscode-html-language-server`
- `vscode-css-language-server`
- `vscode-json-language-server`

### PHP (Intelephense)

```bash
sudo npm install -g intelephense
```

### Java (jdtls)

Requires Java JDK:

```bash
# Install Java JDK
sudo apt-get install -y default-jdk

# Download jdtls
sudo mkdir -p /opt/jdtls
cd /tmp
curl -fsSL "https://download.eclipse.org/jdtls/snapshots/jdt-language-server-latest.tar.gz" -o jdtls.tar.gz
sudo tar -xzf jdtls.tar.gz -C /opt/jdtls
rm jdtls.tar.gz

# Create launcher script
sudo tee /usr/local/bin/jdtls > /dev/null << 'EOF'
#!/bin/bash
JDTLS_HOME="/opt/jdtls"
java \
    -Declipse.application=org.eclipse.jdt.ls.core.id1 \
    -Dosgi.bundles.defaultStartLevel=4 \
    -Declipse.product=org.eclipse.jdt.ls.core.product \
    -noverify \
    -Xmx1G \
    --add-modules=ALL-SYSTEM \
    --add-opens java.base/java.util=ALL-UNNAMED \
    --add-opens java.base/java.lang=ALL-UNNAMED \
    -jar $(find "$JDTLS_HOME/plugins" -name "org.eclipse.equinox.launcher_*.jar" | head -1) \
    -configuration "$JDTLS_HOME/config_linux" \
    -data "${1:-/tmp/jdtls-workspace}" \
    "$@"
EOF
sudo chmod +x /usr/local/bin/jdtls
```

### C# (OmniSharp)

```bash
# Detect architecture
ARCH=$(uname -m)
case $ARCH in
    x86_64) OMNISHARP_ARCH="linux-x64" ;;
    aarch64) OMNISHARP_ARCH="linux-arm64" ;;
esac

# Download and install
sudo mkdir -p /opt/omnisharp
curl -fsSL "https://github.com/OmniSharp/omnisharp-roslyn/releases/download/v1.39.11/omnisharp-${OMNISHARP_ARCH}-net6.0.tar.gz" -o /tmp/omnisharp.tar.gz
sudo tar -xzf /tmp/omnisharp.tar.gz -C /opt/omnisharp
rm /tmp/omnisharp.tar.gz

# Create launcher
sudo tee /usr/local/bin/omnisharp > /dev/null << 'EOF'
#!/bin/bash
/opt/omnisharp/OmniSharp "$@"
EOF
sudo chmod +x /usr/local/bin/omnisharp
sudo chmod +x /opt/omnisharp/OmniSharp
```

### Kotlin

Requires Java JDK:

```bash
# Install Java if not present
sudo apt-get install -y default-jdk

# Download Kotlin Language Server
sudo mkdir -p /opt/kotlin-language-server
curl -fsSL "https://github.com/fwcd/kotlin-language-server/releases/download/1.3.9/server.zip" -o /tmp/kotlin-ls.zip
sudo unzip -q -o /tmp/kotlin-ls.zip -d /opt/kotlin-language-server
rm /tmp/kotlin-ls.zip

# Create symlink
sudo ln -sf /opt/kotlin-language-server/server/bin/kotlin-language-server /usr/local/bin/kotlin-language-server
sudo chmod +x /opt/kotlin-language-server/server/bin/kotlin-language-server
```

## Verify Installation

Check which language servers are installed:

```bash
# Python
pylsp --version

# TypeScript/JavaScript
typescript-language-server --version

# HTML/CSS/JSON
vscode-html-language-server --version
vscode-css-language-server --version
vscode-json-language-server --version

# PHP
intelephense --version

# Java
jdtls --help

# C#
omnisharp --version

# Kotlin
kotlin-language-server --version
```

## Features

When LSP is enabled, you get:

- **Autocomplete**: Smart suggestions as you type
- **Hover Info**: Documentation on hover
- **Go to Definition**: Ctrl+Click to jump to definitions
- **Signature Help**: Parameter hints when calling functions
- **Diagnostics**: Real-time errors and warnings

## Troubleshooting

### LSP not working

1. Check if the language server is installed:
   ```bash
   which pylsp  # or other server
   ```

2. Check CodeHero web logs:
   ```bash
   sudo journalctl -u codehero-web -f
   ```

3. Restart the web service:
   ```bash
   sudo systemctl restart codehero-web
   ```

### Editor works but no autocomplete

- LSP servers are optional - the editor works without them
- Only installed language servers will provide features
- Check browser console for `[LSP]` messages

### Performance issues

- Language servers run on-demand when you open files
- Heavy servers (Java, C#) use more memory
- Close unused tabs to free resources

## Notes

- LSP is optional - the Monaco editor works without it
- Install only the language servers you need
- Some servers require additional dependencies (Java JDK for jdtls/kotlin)
