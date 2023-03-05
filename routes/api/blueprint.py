from flask import Blueprint, g
import aiohttp
from .generate import generate_controller

api_bp = Blueprint('api_bp', __name__)

@api_bp.route('/generate', methods=['POST'])
async def generate_route():
    http_session = aiohttp.ClientSession()
    return await generate_controller(g.s3_client, http_session)