import os
import json
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def read_config_file(file_path):
    try:
        with open(file_path, 'r') as file:
            config = json.load(file)
            if not isinstance(config, list):
                raise ValueError("Configuration file must contain a JSON array.")
            return config
    except FileNotFoundError:
        logging.error(f"Configuration file {file_path} not found.")
        exit(1)
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON from {file_path}.")
        exit(1)
    except ValueError as ve:
        logging.error(str(ve))
        exit(1)

def validate_command(command):
    disallowed_chars = {'&', ';', '|', '`', '$', '<', '>', '(', ')'}
    for char in disallowed_chars:
        if char in command:
            logging.error(f"Command '{command}' contains disallowed character '{char}'.")
            exit(1)

def tokenize_command(command):
    import shlex
    return shlex.split(command)

def execute_commands(commands):
    for cmd in commands:
        logging.info(f"Starting command: {cmd}")
        try:
            result = subprocess.run(tokenize_command(cmd), check=True)
            logging.info(f"Command completed successfully: {cmd}")
        except subprocess.CalledProcessError as cpe:
            logging.error(f"Command failed: {cmd} with return code {cpe.returncode}")
            exit(cpe.returncode)

def main():
    config_file_path = 'deploy_config.json'
    main_commands = read_config_file(config_file_path)
    
    app_init_cmd = os.getenv('APP_INIT_CMD')
    if app_init_cmd:
        validate_command(app_init_cmd)
        main_commands.append(app_init_cmd)
    
    for cmd in main_commands:
        validate_command(cmd)
    
    execute_commands(main_commands)

if __name__ == '__main__':
    main()