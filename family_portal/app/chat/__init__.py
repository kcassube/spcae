from flask import Blueprint
bp = Blueprint('chat', __name__, template_folder='../templates/chat')

# Routen werden einmalig importiert
from . import routes  # noqa
