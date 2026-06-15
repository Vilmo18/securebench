import os
import subprocess

def execute_task(task, config):
    # Validate the task name
    if task not in ["task1", "task2"]:
        return "Invalid task"

    # Read the configuration file
    try:
        with open(config) as f:
            config = f.read()
    except FileNotFoundError:
        return "Configuration file not found"

    # Validate the configuration file contents
    if not config.startswith("user_role=admin"):
        return "Unauthorized access"

    # Resolve the command path
    cmd = "/usr/local/bin/" + task

    # Execute the command
    try:
        subprocess.run(cmd, shell=True)
    except Exception as e:
        return "Error executing command"

    # Return a success message
    return "Task executed successfully"