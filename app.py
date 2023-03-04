from flask import Flask

from routes.api.api import api_bp

from middleware.session import session_middleware

app = Flask(__name__)

app.register_blueprint(api_bp, url_prefix='/api')
session_middleware(app)

@app.route('/')
def index():
    return (
        "Welcome to the Photo Processing Service\n"
        + "Here are the available endpoints:\n"
        + "/api/generate  -  creates photos based on event taken in\n"
    )

if __name__ == '__main__':
  app.run(debug=True, load_dotenv=True)
