from flask import Flask, render_template
from .extensions import db, migrate, login_manager
from .config import DevelopmentConfig
import os

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(DevelopmentConfig)
    os.makedirs(app.instance_path, exist_ok=True)
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    
    from .models import Usuario
    
    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))
    
    from .patrimonio import bp as patrimonio_bp
    # Prefixa todas as rotas do app sob /patrimonio
    app.register_blueprint(patrimonio_bp, url_prefix='/patrimonio')
    
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/patrimonio')

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500

    return app 