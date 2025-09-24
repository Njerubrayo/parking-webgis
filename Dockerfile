# Use slim Python base
ARG PYTHON_VERSION=3.10-slim
FROM python:${PYTHON_VERSION}

# Prevent Python from writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies: Postgres, GDAL, build tools
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    g++ \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Fix GDAL library path (symlink to versioned .so)
RUN find /usr/lib/x86_64-linux-gnu/ -name "libgdal.so.*" -exec ln -sf {} /usr/lib/x86_64-linux-gnu/libgdal.so \; -quit



# Set GDAL include paths (helps pip find headers)
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Create app directory
RUN mkdir -p /code
WORKDIR /code

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /tmp/requirements.txt \
    && rm -rf /root/.cache/

# Copy project code
COPY . /code

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Start Gunicorn server
CMD ["gunicorn", "--bind", ":8000", "--workers", "2", "parking_system.wsgi"]
