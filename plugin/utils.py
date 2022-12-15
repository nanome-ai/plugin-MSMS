import re

def natural_sorted(l):
    convert = lambda text: int(text) if text.isdigit() else text
    natural_key = lambda key: [convert(c) for c in re.split('(\d+)', key)]
    return sorted(l, key=natural_key)
