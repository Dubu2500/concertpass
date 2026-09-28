# Imagen base ligera con Python
FROM python:3.12-slim

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Primero las dependencias, para aprovechar la caché de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Luego el código
COPY main.py .

# Puerto donde escucha la app
EXPOSE 8080

# Usuario no-root por seguridad
RUN useradd app
USER app

# Arranca el servidor
# Las credenciales de la BD NO van aquí: se pasan con -e en docker run
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
