# Installation Reference

## Prerequisites

- Python 3.14 or higher
- [uv](https://github.com/astral-sh/uv) package manager

## Install from Source

```bash
# Clone the repository
git clone https://github.com/dnvriend/claude-code-scheduler.git
cd claude-code-scheduler

# Install globally with uv
uv tool install .
```

## Install with mise (Recommended for Development)

```bash
cd claude-code-scheduler
mise trust
mise install
uv sync
uv tool install .
```

## Verify Installation

```bash
claude-code-scheduler --version
```

## Shell Completion

### Supported Shells

| Shell | Version Requirement | Status |
|-------|-------------------|--------|
| **Bash** | ≥ 4.4 | ✅ Supported |
| **Zsh** | Any recent version | ✅ Supported |
| **Fish** | ≥ 3.0 | ✅ Supported |
| **PowerShell** | Any version | ❌ Not Supported |

### Quick Setup (Temporary)

```bash
# Bash - active for current session only
eval "$(claude-code-scheduler completion bash)"

# Zsh - active for current session only
eval "$(claude-code-scheduler completion zsh)"

# Fish - active for current session only
claude-code-scheduler completion fish | source
```

### Permanent Setup (Recommended)

```bash
# Bash - add to ~/.bashrc
echo 'eval "$(claude-code-scheduler completion bash)"' >> ~/.bashrc
source ~/.bashrc

# Zsh - add to ~/.zshrc
echo 'eval "$(claude-code-scheduler completion zsh)"' >> ~/.zshrc
source ~/.zshrc

# Fish - save to completions directory
mkdir -p ~/.config/fish/completions
claude-code-scheduler completion fish > ~/.config/fish/completions/claude-code-scheduler.fish
```

### File-based Installation (Better Performance)

For better shell startup performance, generate completion scripts to files:

```bash
# Bash
claude-code-scheduler completion bash > ~/.claude-code-scheduler-complete.bash
echo 'source ~/.claude-code-scheduler-complete.bash' >> ~/.bashrc

# Zsh
claude-code-scheduler completion zsh > ~/.claude-code-scheduler-complete.zsh
echo 'source ~/.claude-code-scheduler-complete.zsh' >> ~/.zshrc

# Fish (automatic loading from completions directory)
mkdir -p ~/.config/fish/completions
claude-code-scheduler completion fish > ~/.config/fish/completions/claude-code-scheduler.fish
```

### Completion Usage

Once installed, completion works automatically:

```bash
# Tab completion for commands
claude-code-scheduler <TAB>
# Shows: gui, cli, debug, completion

# Tab completion for options
claude-code-scheduler --<TAB>
# Shows: --verbose --version --help

# Tab completion for shell types
claude-code-scheduler completion <TAB>
# Shows: bash zsh fish
```

## Security Tool Prerequisites

gitleaks must be installed separately for security scanning:

```bash
# macOS
brew install gitleaks

# Linux
# See: https://github.com/gitleaks/gitleaks#installation
```

## Uninstall

```bash
uv tool uninstall claude-code-scheduler
```

## Upgrading

```bash
cd claude-code-scheduler
git pull
uv tool install . --reinstall
```
