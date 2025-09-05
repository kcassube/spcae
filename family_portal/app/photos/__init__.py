from flask import Blueprint
bp = Blueprint('photos', __name__, template_folder='../templates/photos')

from . import routes  # noqa
from app.photos import routes
