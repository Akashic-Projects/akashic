
def remove_quotes(s):
    """
    """
    
    if (s.startswith("\"") and s.endswith("\"")) or \
    (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def to_clips_quotes(s):
    return s.replace("'", '"')