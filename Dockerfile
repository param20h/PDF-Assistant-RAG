FROM python:3.9-slim

# Prevent Python from writing pyc files and keep stdout/stderr unbuffered
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the Hugging Face requested default port, but allow overriding (e.g., Render)
ENV PORT=7860

# Create a non-root user (Required for Hugging Face Spaces)
RUN useradd -m -u 1000 user
USER user

# Set up the HOME and PATH variables
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy the requirements file and install dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files with proper permissions
COPY --chown=user . .

# Ensure data directories exist and are writable
RUN mkdir -p uploads vectorstore static/profile_pics && \
    chmod -R 777 uploads vectorstore static/profile_pics

# Expose the target port
EXPOSE $PORT

# Start the Flask app using Gunicorn (production server)
CMD ["sh", "-c", "gunicorn app:app --workers 2 --timeout 120 --bind 0.0.0.0:$PORT"]
