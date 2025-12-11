import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(os.path.dirname(__file__), '../instance/app.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    APPLICATION_ROOT = os.environ.get('APPLICATION_ROOT', '/')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False 