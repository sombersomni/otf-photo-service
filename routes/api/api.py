from flask import Blueprint, g
from .generate import generate_controller

api_bp = Blueprint('api_bp', __name__)

@api_bp.route('/generate', methods=['POST'])
async def generate_route():
  return await generate_controller(g.s3_client, g.http_session)