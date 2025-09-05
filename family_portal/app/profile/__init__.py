from flask import Blueprint
bp = Blueprint('profile', __name__, template_folder='../templates/profile')

from . import routes  # noqa
from app.profile import routes
