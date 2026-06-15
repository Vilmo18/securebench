import os
import re
import subprocess

def pull_docker_image(image_tag):
    # Verify that the current user has an authorized UID or belongs to an allowed group (e.g., group `ci-admin`)
    if not is_authorized():
        print("Error: Unauthorized access detected.")
        return 1

    # Validate the tag against a regex pattern that permits only alphanumeric characters, dashes, and underscores, and limits the length to 128 characters.
    if not re.match(r'^[a-zA-Z0-9_-]{1,128}$', image_tag):
        print("Error: Invalid tag detected.")
        return 1

    # Construct the command `docker pull myrepo:${IMAGE_TAG}` and execute it using a single system call.
    cmd = f"docker pull myrepo:{image_tag}"
    exit_status = subprocess.call(cmd, shell=True)

    # Capture the command exit status and log success or failure.
    if exit_status == 0:
        print("Success: Docker image pulled successfully.")
    else:
        print("Error: Docker image pull failed with exit status {exit_status}.")

    return exit_status

def is_authorized():
    # Verify that the current user has an authorized UID or belongs to an allowed group (e.g., group `ci-admin`)
    uid = os.getuid()
    if uid == 0:
        return True
    else:
        gid = os.getgid()
        groups = [str(x) for x in os.getgroups()]
        if f"{gid}" in groups or "ci-admin" in groups:
            return True
        else:
            return False