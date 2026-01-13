import sys
import shlex
import readline
import shell_utils as utils

def main():
    completer = utils.ShellCompleter()
    readline.set_completer(completer.complete)

    if 'libedit' in readline.__doc__: 
        readline.parse_and_bind("bind ^I rl_complete")
    else: 
        readline.parse_and_bind("tab: complete")
    
    readline.parse_and_bind("set show-all-if-ambiguous off")
    readline.set_completer_delims(' \t\n')

    
    try:
        readline.set_completion_display_matches_hook(utils.display_matches)
    except AttributeError:
        pass

    utils.print_banner()

    
    while True:
        try:
            command_input = input("$ ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        
        if not command_input.strip():
            continue

        parts = shlex.split(command_input)
        if not parts: continue

        if "|" in parts:
            utils.execute_pipeline(parts)
        else:
            proc = utils.run_command_segment(parts, None, sys.stdout, sys.stderr)
            if proc:
                proc.wait()

if __name__ == "__main__":
    main()