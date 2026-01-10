import sys
import os
import subprocess
import shlex
import readline
import random

class ShellCompleter:
    def __init__(self):
        self.path_commands = self._get_all_path_commands()

    def _get_all_path_commands(self):
        commands = {"echo", "exit", "type", "pwd", "cd", "history"} 
        paths = os.environ.get("PATH", "").split(os.pathsep)
        for p in paths:
            if os.path.isdir(p):
                try:
                    for filename in os.listdir(p):
                        full = os.path.join(p, filename)
                        if os.access(full, os.X_OK):
                            commands.add(filename)
                except OSError:
                    continue
        return sorted(list(commands))
    def complete(self, text, state):
        if state == 0:
            
            begidx = readline.get_begidx()
            is_command = (begidx == 0)

            self.matches = []

            if is_command:
                self.matches = [c + " " for c in self.path_commands if c.startswith(text)]
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
    print(" ".join(matches)) 
    sys.stdout.write("$ " + readline.get_line_buffer())
    sys.stdout.flush()

def run_command_segment(parts, input_fd, output_fd, error_fd):   
   
        stdout_dest = output_fd
        stderr_dest = error_fd
            
        should_close_stdout = False
        should_close_stderr = False

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
                
                if should_close_stderr:
                    stderr_dest.close() 
                stderr_dest = f
                should_close_stderr = True
            else:
                if should_close_stdout:
                    stdout_dest.close()
                stdout_dest = f
                should_close_stdout = True
            del parts[index:index + 2]

        
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
            output_buffer = [] 
            target = args[0] if args else ""
            target = args[0] if args else ""
        
            if target in ("type", "echo", "exit", "pwd", "cd", "history"):
                output_buffer.append(f"{target} is a shell builtin")
            else:
                found = False
                for d in path_dirs: 
                    full_path = os.path.join(d, target) 
                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK): 
                        output_buffer.append(f"{target} is {full_path}")
                        found = True
                        break
                if not found:
                    print(f"{target}: not found", file=safe_stderr)
            
            if output_buffer:
                write_to_output("\n".join(output_buffer), safe_stdout)
                
            if should_close_stdout: stdout_dest.close()
            return None


        elif command == "pwd":
            write_to_output(os.getcwd(), safe_stdout)
            if should_close_stdout: stdout_dest.close()
            return None
        
        elif command == "history":
            if args:
                history_length = len(args)
                history_output = []
                n = int(args[0])
                total_history = readline.get_current_history_length()
                start_index = max(1, total_history - n+ 1)
                for i in range(start_index, total_history + 1):
                    history_output.append(f"{i}  {readline.get_history_item(i)}")
                write_to_output("\n".join(history_output), safe_stdout)
                if should_close_stdout: stdout_dest.close()
                return None


            else:
                history_length = readline.get_current_history_length()
                history_output = []
                for i in range(1, history_length + 1):
                    history_output.append(f"{i}  {readline.get_history_item(i)}")
                write_to_output("\n".join(history_output), safe_stdout)
                if should_close_stdout: stdout_dest.close()
                return None


        elif command == "cd":
            if len(parts) > 1:
                path= os.path.expanduser(parts[1])
                try:
                    os.chdir(path)
                except FileNotFoundError:
                    print(f"cd: {parts[1]}: No such file or directory", file=stderr_dest)
            else:
                os.chdir(os.path.expanduser("~"))
        else:
            try:
                proc = subprocess.Popen(
                parts, 
                stdin=input_fd, 
                stdout=safe_stdout, 
                stderr=safe_stderr
            )
                return proc
        
            except FileNotFoundError:
                    print(f"{command}: command not found", file=stderr_dest)
        if should_close_stdout:
            stdout_dest.close()
        if should_close_stderr:
            stderr_dest.close()

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

        if not is_last:
            if proc: 
                os.close(stdout_fd) 
            
        if proc:
            children.append(proc)
            
        
        next_stdin = next_read_fd

    for proc in children:
        proc.wait()


def print_banner():
    banner = r"""

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

def main():
 
    completer = ShellCompleter()
    readline.set_completer(completer.complete)

    if 'libedit' in readline.__doc__: 
        readline.parse_and_bind("bind ^I rl_complete")
    else: 
        readline.parse_and_bind("tab: complete")
    readline.parse_and_bind("set show-all-if-ambiguous off")
    readline.parse_and_bind("set bell-style audible")
    readline.set_completer_delims(' \t\n')
    readline.parse_and_bind('"\x1b[A": history-search-backward')
    readline.parse_and_bind('"\x1b[B": history-search-forward')

    try:
        readline.set_completion_display_matches_hook(display_matches)
    except AttributeError:
        pass

    print_banner()

    while True:
        try:
            command_input = input("$ ")
            

        except (EOFError, KeyboardInterrupt):
            print()
            break
        
        if not command_input.strip():
            continue

        parts = shlex.split(command_input)
        if not parts:
            continue

        
        if "|" in parts:
            execute_pipeline(parts)
        else:
            proc = run_command_segment(parts, None, sys.stdout, sys.stderr)
            if proc:
                proc.wait()

if __name__ == "__main__":
    main()
