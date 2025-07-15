from flask import Flask, render_template
from .extensions import db, migrate
from .config import DevelopmentConfig
import os

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(DevelopmentConfig)
    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    from .patrimonio import bp as patrimonio_bp
    app.register_blueprint(patrimonio_bp)

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500

    return app 