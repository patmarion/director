
def push_variables(**kwargs):
    globals().update(kwargs)

def update_context(context_dict):
    globals().update(context_dict)

def get_context():
    return globals()