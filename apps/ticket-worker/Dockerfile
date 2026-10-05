# Imagen base ligera con Python
FROM python:3.12-slim

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Primero las dependencias, para aprovechar la caché de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Luego el código
COPY worker.py .

# Usuario no-root por seguridad
RUN useradd app
USER app

# -u para que los print salgan al instante en docker logs
CMD ["python", "-u", "worker.py"]
