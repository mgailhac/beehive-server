from . import nodeDash

@nodeDash.route('/')
def admin_root():
    return 'You found nodeDash!!!'
