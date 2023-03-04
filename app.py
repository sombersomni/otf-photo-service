from flask import Flask

from routes.api.blueprint import api_bp
from middleware.s3 import s3_middleware

app = Flask(__name__)

app.register_blueprint(api_bp)
s3_middleware(app)

@app.route('/')
def index():
    return (
        "Welcome to the Photo Processing Service\n"
        + "Here are the available endpoints:\n"
        + "/generate  -  creates photos based on event taken in\n"
    )

if __name__ == '__main__':
  app.run(debug=True, load_dotenv=True)
