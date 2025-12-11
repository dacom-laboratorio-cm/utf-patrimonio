from app import create_app
import logging
from logging.handlers import RotatingFileHandler
import os

app = create_app()

if __name__ == '__main__':
    # Configuração básica de logging
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=5)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Aplicação iniciada')
    app.run(debug=False, host='0.0.0.0', port=5001) 