from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
import subprocess

# init SQLAlchemy so we can use it later in our models
db = SQLAlchemy()

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://%s:%s@localhost/analog_collective' % (
os.environ['DB_USER'], os.environ['DB_PASS'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

js_env = subprocess.Popen("{} > env.js".format(os.path.join(os.getcwd(), 'project', 'env.sh')),
                          shell=True, cwd=os.path.join(os.getcwd(), 'project', 'static'))

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

from .models import Users


@login_manager.user_loader
def load_user(user_id):
	# since the user_id is just the primary key of our user table, use it in the query for the user
	return Users.query.get(int(user_id))


# blueprint for auth routes in our app
from .auth import auth as auth_blueprint

app.register_blueprint(auth_blueprint)

# blueprint for non-auth parts of app
from .main import main as main_blueprint
from .payment import payment as payment_blueprint

app.register_blueprint(main_blueprint)
app.register_blueprint(payment_blueprint)
