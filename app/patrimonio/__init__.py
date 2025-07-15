from flask import Blueprint

bp = Blueprint('patrimonio', __name__, template_folder='../templates')

from . import routes 