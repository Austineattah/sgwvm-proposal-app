# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for OpenCV and PyZbar
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libzbar0 \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies list
COPY requirements.txt .

# Install Python requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy full application code
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Configure Streamlit environment
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Healthcheck to ensure container stability
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Launch NEXUSVAULT Engine
CMD ["streamlit", "run", "app.py"]