import base64
import json
import pickle
from subprocess import run, PIPE

def execute(payload):
    try:
        data = base64.b64decode(payload)
        command, args = pickle.loads(data)
        result = run([command] + args, stdout=PIPE, stderr=PIPE)
        return result.stdout.decode('utf-8')
    except (pickle.UnpicklingError, subprocess.CalledProcessError) as e:
        raise ValueError(str(e)) from None