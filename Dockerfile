FROM --platform=linux/amd64 python:3.10-slim

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    PyPDF2==3.0.1

# Copy the processing script
COPY process_collections.py .

# Run the script
CMD ["python", "process_collections.py"]
