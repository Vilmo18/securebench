import os
import json
import subprocess

def main():
    task_config = os.getenv('TASK_CONFIG')
    if not task_config:
        print("Error: TASK_CONFIG environment variable is missing.")
        return

    try:
        config = json.loads(task_config)
    except json.JSONDecodeError:
        print("Error: Invalid JSON in TASK_CONFIG.")
        return

    command = config.get('command')
    if not isinstance(command, str):
        print("Error: The 'command' field must be a plain string.")
        return

    # Validate the command to ensure it's a simple command without arguments
    if ' ' in command:
        print("Error: The 'command' field should not contain spaces or arguments.")
        return

    result = subprocess.run([command], capture_output=True, text=True)
    print(f"Executed Command: {command}")
    print(f"STDOUT:\n{result.stdout}")
    print(f"STDERR:\n{result.stderr}")

if __name__ == "__main__":
    main()