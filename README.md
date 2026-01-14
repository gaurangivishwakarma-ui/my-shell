# my-shell
SeaShell is a lightweight, POSIX-compliant command-line interpreter built entirely in Python. It bridges the gap between high-level Python scripting and low-level system process management. The shell features a robust REPL (Read-Eval-Print Loop) capable of handling complex command pipelines, standard I/O redirection, and interactive auto-completion, mimicking the behavior of established shells like Bash or Zsh.
Key Features

~Unix Pipelines (|): Full implementation of inter-process communication using os.pipe(). Supports chaining multiple commands (e.g., ls | grep .py | wc -l) where data streams seamlessly from one process to the next without blocking.

~I/O Redirection: sophisticated handling of standard output and standard error streams.
    1. Overwrite: > (stdout), 2> (stderr).
    2. Append: >> (stdout), 2>> (stderr).

~Intelligent Auto-Completion: Custom readline completer that supports:

~Command Completion: Scans the system PATH to autocomplete executable names (using TRIE).

~File Path Completion: Context-aware completion for directories and files within the current workspace.

~Built-in Command Suite: Native Python implementations of core shell utilities:
    1. cd: Supports relative paths, absolute paths, and home directory expansion.
    2. history: View session history with optional numeric limits (e.g., history 5).
    3. type: Distinguishes between shell built-ins and external executables.
    4. pwd & echo: Standard environment reporting and text output.

~Smart History Navigation: configured with history-search-backward logic, allowing users to type a partial command (e.g., git) and press Up Arrow to search only matching commands from history.

~External Command Execution: Uses subprocess.Popen to launch and manage system executables, ensuring compatibility with all standard Linux/Unix binaries.
