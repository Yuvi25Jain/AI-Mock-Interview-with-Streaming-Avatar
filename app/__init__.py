from flask import Flask
from app.config import Config

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    
    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_object(Config)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Initialize Config (creates upload folders)
    Config.init_app(app)

    # Initialize Database
    from . import db
    db.init_app(app)

    # Initialize Database
    from . import db
    db.init_app(app)
    
    # Register Blueprints
    from .routes import auth, dashboard, interview, api
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(interview.bp)
    app.register_blueprint(api.bp)

    return app