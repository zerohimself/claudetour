# Proper ClauDEtour Installation

## Current Setup (Development)
- Script: `/home/zerohimself/ml_research/claudetour_project/bin/bash`
- Symlink: `/home/zerohimself/bash-fixer`
- Shell: Points to symlink in `/etc/passwd`

## Recommended Production Setup

### Option 1: User Install (Recommended)
```bash
# Create local bin directory
mkdir -p ~/.local/bin

# Copy the interceptor
cp /home/zerohimself/ml_research/claudetour_project/bin/bash ~/.local/bin/claudetour

# Update your shell
chsh -s ~/.local/bin/claudetour

# Create config directory
mkdir -p ~/.config/claudetour
```

### Option 2: System Install
```bash
# Create system directory
sudo mkdir -p /opt/claudetour/bin

# Copy interceptor
sudo cp /home/zerohimself/ml_research/claudetour_project/bin/bash /opt/claudetour/bin/claudetour

# Make executable
sudo chmod +x /opt/claudetour/bin/claudetour

# Add to shells
echo "/opt/claudetour/bin/claudetour" | sudo tee -a /etc/shells

# Change shell
chsh -s /opt/claudetour/bin/claudetour
```

## Benefits of Proper Installation
1. **Separation of concerns** - source code vs runtime
2. **Easy updates** - pull changes without affecting running instance
3. **Multiple versions** - test new versions before deploying
4. **Clean uninstall** - remove without affecting source

## Migration Steps
1. Install to new location
2. Update shell in `/etc/passwd`
3. Log out/in to test
4. Remove old symlinks once confirmed working