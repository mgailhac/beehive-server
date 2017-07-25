from flask import Blueprint

nodeDash = Blueprint(
    'nodeDash',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import views
