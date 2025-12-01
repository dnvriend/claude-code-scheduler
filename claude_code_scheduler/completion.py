"""Shell completion script generator for claude-code-scheduler.

This module provides a Click command that generates shell completion scripts
for bash, zsh, and fish shells.

Key Components:
    - completion_command: CLI command to generate completion scripts

Dependencies:
    - click: CLI framework and shell completion classes
    - click.shell_completion: BashComplete, ZshComplete, FishComplete

Related Modules:
    - cli: Registers completion_command as a subcommand

Called By:
    - cli.main: Registered via main.add_command(completion_command)

Example:
    >>> # Generate bash completion script
    >>> claude-code-scheduler completion bash
    >>> # Install to shell
    >>> eval "$(claude-code-scheduler completion zsh)"

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

import click
from click.shell_completion import BashComplete, FishComplete, ShellComplete, ZshComplete


@click.command(name="completion")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"], case_sensitive=False))
def completion_command(shell: str) -> None:
    """Generate shell completion script.

    SHELL: The shell type (bash, zsh, fish)

    Install instructions:

    \b
    # Bash (add to ~/.bashrc):
    eval "$(claude-code-scheduler completion bash)"

    \b
    # Zsh (add to ~/.zshrc):
    eval "$(claude-code-scheduler completion zsh)"

    \b
    # Fish (add to ~/.config/fish/completions/claude-code-scheduler.fish):
    claude-code-scheduler completion fish > ~/.config/fish/completions/claude-code-scheduler.fish

    \b
    File-based Installation (Recommended for better performance):

    \b
    # Bash
    claude-code-scheduler completion bash > ~/.claude-code-scheduler-complete.bash
    echo 'source ~/.claude-code-scheduler-complete.bash' >> ~/.bashrc

    \b
    # Zsh
    claude-code-scheduler completion zsh > ~/.claude-code-scheduler-complete.zsh
    echo 'source ~/.claude-code-scheduler-complete.zsh' >> ~/.zshrc

    \b
    # Fish (automatic loading)
    mkdir -p ~/.config/fish/completions
    claude-code-scheduler completion fish > ~/.config/fish/completions/claude-code-scheduler.fish

    \b
    Supported Shells:
      - Bash (≥ 4.4)
      - Zsh (any recent version)
      - Fish (≥ 3.0)

    \b
    Note: PowerShell is not currently supported by Click's completion system.
    """
    ctx = click.get_current_context()

    # Get the appropriate completion class
    completion_classes: dict[str, type[ShellComplete]] = {
        "bash": BashComplete,
        "zsh": ZshComplete,
        "fish": FishComplete,
    }

    completion_class = completion_classes.get(shell.lower())
    if completion_class:
        completer = completion_class(
            cli=ctx.find_root().command,
            ctx_args={},
            prog_name="claude-code-scheduler",
            complete_var="_CLAUDE_CODE_SCHEDULER_COMPLETE",
        )
        click.echo(completer.source())
    else:
        raise click.BadParameter(f"Unsupported shell: {shell}")
