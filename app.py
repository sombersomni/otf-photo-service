from flask import Flask
from flask_cors import CORS

from routes.api.blueprint import api_bp

from middleware.session import session_middleware

app = Flask(__name__)
# register routes
app.register_blueprint(api_bp, url_prefix='/api')
# register middleware
session_middleware(app)
cors = CORS(app)
cors = CORS(app, resources={
    r"/*": {
        "origins": "http://localhost:3000"
    }
})

@app.route('/')
def index():
    return (
        "Welcome to the Photo Processing Service\n"
        + "Here are the available endpoints:\n"
        + "/api/generate  -  creates photos based on event taken in\n"
    )

if __name__ == '__main__':
  app.run(load_dotenv=True)
