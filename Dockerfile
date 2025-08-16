# Dockerfile pentru Render deployment
FROM python:3.11-slim

# Setează directorul de lucru
WORKDIR /app

# Copiază requirements.txt și instalează dependențele
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiază toate fișierele aplicației
COPY . .

# Expune portul
EXPOSE 10000

# Setează variabilele de mediu
ENV PYTHONUNBUFFERED=1
ENV PORT=10000

# Rulează aplicația
CMD ["python", "app.py"]