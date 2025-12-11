# Utiliza imagem oficial do Python
FROM python:3.12-slim

# Define diretório de trabalho
WORKDIR /app

# Copia arquivos de dependências
COPY requirements.txt ./

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código
COPY . .

# Define variáveis de ambiente para Flask
ENV FLASK_APP=run.py
ENV FLASK_ENV=development

# Expõe a porta padrão do Flask
EXPOSE 5001

# Comando para rodar o Flask
CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"] 