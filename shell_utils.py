import sys
import os
import subprocess
import readline
import random
import shutil

class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_word = True

    def find_matches(self, prefix):
        node = self.root

        for char in prefix:
            if char not in node.children:
                return [] 
            node = node.children[char]
        
        
        results = []
        self._dfs(node, prefix, results)
        return results

    def _dfs(self, node, current_prefix, results):
        if node.is_end_of_word:
            results.append(current_prefix)
        for char in sorted(node.children.keys()):
            self._dfs(node.children[char], current_prefix + char, results)



class ShellCompleter:
    def __init__(self):
        self.command_trie = Trie()
        self._populate_command_trie()

    def _populate_command_trie(self):
        builtins = {"echo", "exit", "type", "pwd", "cd", "history"}
        for cmd in builtins:
            self.command_trie.insert(cmd)

        paths = os.environ.get("PATH", "").split(os.pathsep)
        seen_files = set(builtins)
        seen_paths = set()

        for p in paths:
            if p in seen_paths or not os.path.isdir(p):
                continue
            seen_paths.add(p)

            try:
                with os.scandir(p) as entries:
                    for entry in entries:
                        if entry.is_file() and entry.name not in seen_files:
                            if os.access(entry.path, os.X_OK):
                                self.command_trie.insert(entry.name)
                                seen_files.add(entry.name)
            except OSError:
                continue

    def complete(self, text, state):
        if state == 0:
            begidx = readline.get_begidx()
            is_command = (begidx == 0)

            self.matches = []

            if is_command:
                raw_matches = self.command_trie.find_matches(text)
                self.matches = [c + " " for c in raw_matches]
            else:
                dirname, partial = os.path.split(text)
                search_dir = dirname if dirname else "."
                
                if os.path.isdir(search_dir):
                    try:
                        for filename in os.listdir(search_dir):
                            if filename.startswith(partial):
                                full_path = os.path.join(search_dir, filename)
                                display_name = os.path.join(dirname, filename) if dirname else filename
                                
                                if os.path.isdir(full_path):
                                    display_name += "/"
                                else:
                                    display_name += " " 
                                self.matches.append(display_name)
                    except OSError:
                        pass
                self.matches.sort()
        
        try:
            return self.matches[state]
        except IndexError:
            return None


path_dirs = os.environ["PATH"].split(os.pathsep)

def display_matches(_, matches, _longest_match_length):
    print() 
    print("  ".join([m.strip() for m in matches])) 
    sys.stdout.write("$ " + readline.get_line_buffer())
    sys.stdout.flush()

def run_command_segment(parts, input_fd, output_fd, error_fd):   
        stdout_dest = output_fd
        stderr_dest = error_fd
        should_close_stdout = False
        should_close_stderr = False

        # Handle Redirection
        operator_indices = [i for i, part in enumerate(parts) if part in (">", ">>", "1>","1>>", "2>", "2>>")]
        for index in reversed(operator_indices):
            operator = parts[index]
            if index + 1 >= len(parts):
                print("Syntax error: no file specified for redirection")
                continue
            filename = parts[index + 1]
            mode = "w"
            if ">>" in operator:
                    mode = "a"
            try:
                f = open(filename, mode)
            except IOError as e:
                print(f"Error opening file {filename}: {e}")
                continue

            if operator in ("2>", "2>>"):
                if should_close_stderr: stderr_dest.close() 
                stderr_dest = f
                should_close_stderr = True
            else:
                if should_close_stdout: stdout_dest.close()
                stdout_dest = f
                should_close_stdout = True
            del parts[index:index + 2]

        if not parts: return None
        command = parts[0]
        args = parts[1:]

        safe_stdout = stdout_dest if stdout_dest else sys.stdout
        safe_stderr = stderr_dest if stderr_dest else sys.stderr

        def write_to_output(text, dest):
            if isinstance(dest, int):
                with os.fdopen(dest, 'w') as f:
                    f.write(str(text) + "\n")
            else:
                print(text, file=dest)

        if command == "exit":
            sys.exit(0)

        elif command == "echo":
            write_to_output(" ".join(args), safe_stdout)
            if should_close_stdout: stdout_dest.close()
            return None
        
        elif command == "type":
            target = args[0] if args else ""
            if not target: return None

            if target in ("type", "echo", "exit", "pwd", "cd", "history"):
                print(f"{target} is a shell builtin", file=safe_stdout)
            else:
                location = shutil.which(target)
                if location:
                    print(f"{target} is {location}", file=safe_stdout)
                else:
                    print(f"{target}: not found", file=safe_stderr)
            
            if should_close_stdout: stdout_dest.close()
            return None

        elif command == "pwd":
            write_to_output(os.getcwd(), safe_stdout)
            if should_close_stdout: stdout_dest.close()
            return None
        
        elif command == "history":
            history_length = readline.get_current_history_length()
            start_index = 1
            if args:
                try:
                    n = int(args[0])
                    start_index = max(1, history_length - n + 1)
                except ValueError:
                    pass
            
            history_output = []
            for i in range(start_index, history_length + 1):
                history_output.append(f"{i}  {readline.get_history_item(i)}")
            write_to_output("\n".join(history_output), safe_stdout)
            if should_close_stdout: stdout_dest.close()
            return None

        elif command == "cd":
            if len(parts) > 1:
                path = os.path.expanduser(parts[1])
                try:
                    os.chdir(path)
                except FileNotFoundError:
                    print(f"cd: {parts[1]}: No such file or directory", file=stderr_dest)
            else:
                os.chdir(os.path.expanduser("~"))
            if should_close_stdout: stdout_dest.close()
            return None
        else:
            try:
                proc = subprocess.Popen(parts, stdin=input_fd, stdout=safe_stdout, stderr=safe_stderr)
                return proc
            except FileNotFoundError:
                print(f"{command}: command not found", file=stderr_dest)
        
        if should_close_stdout: stdout_dest.close()
        if should_close_stderr: stderr_dest.close()

def execute_pipeline(parts):
    commands = []
    current_cmd = []
    for part in parts:
        if part == "|":
            if current_cmd:
                commands.append(current_cmd)
            current_cmd = []
        else:
            current_cmd.append(part)
    if current_cmd:
        commands.append(current_cmd)
 
    next_stdin = None 
    children = []
    
    for i, cmd_parts in enumerate(commands):
        is_last = (i == len(commands) - 1)
        if is_last:
            stdout_fd = sys.stdout 
            next_read_fd = None
        else:
            r, w = os.pipe()
            stdout_fd = w
            next_read_fd = r
       
        proc = run_command_segment(cmd_parts, next_stdin, stdout_fd, sys.stderr)
        
        if next_stdin is not None and isinstance(next_stdin, int):
            os.close(next_stdin)
        if not is_last and proc: 
            os.close(stdout_fd) 
            
        if proc:
            children.append(proc)
        
        next_stdin = next_read_fd

    for proc in children:
        proc.wait()

def print_banner():
    banner = r"""

    new shell, who dis?
            ___
        .-"; ! ;"-.
      .'!  : | :  !`.
     /\  ! : ! : !  /\
    /\ |  ! :|: !  | /\
   (  \ \ ; :!: ; / /  )
  ( `. \ | !:|:! | / .' )
  (`. \ \ \!:|:!/ / / .')
   \ `.`.\ |!|! |/,'.' /
    `._`.\\\!!!// .'_.'
       `.`.\\|//.'.'
        |`._`n'_.'|  
        "----^----"

    Shell improvements:
        - faster command completion using Trie
        - better file system traversal
        - improved redirection handling
    """
    puns = [
        "Shell we begin?",
        "I'm shore you'll love this shell.",
        "Don't be salty if I crash.",
        "It's a shore thing.",
        "Stop being so shellfish with your RAM.",
        "This shell is shrimply the best.",
        "What the shell is going on?",
        "Pearl of wisdom: Don't run 'rm -rf /'",
        "I sea what you typed there.",
        "I promise I'm not a sh-am.",
        "Sudo make me a sandwich.",
        "Feeling crabby? This shell can help.",
        "Time to clam up and code.",
        "Resting Beach Face (Standard Output)."
    ]
    print(banner)
    print(f"   {random.choice(puns)}")
    print("   Type 'exit' to wave goodbye.\n")
    print("--------------------------------------------------\n")