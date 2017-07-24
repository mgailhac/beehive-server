from flask import Blueprint

nodeDash = Blueprint(
    'nodeDash',
    __name__,
    template_folder='templates',
)

from . import views
