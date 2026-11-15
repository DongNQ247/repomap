import json

def save(u):
    return json.dumps(u)

def load(s):
    return json.loads(s)
