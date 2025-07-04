# Use a slim Python image for a smaller final container size
FROM python:3.11-slim

# Install git and build-essential
RUN apt-get update && apt-get install -y git build-essential

# Set environment variable to prevent protobuf error
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker's build cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose the port the API server will run on
EXPOSE 8000

# The command to run when the container starts
# Rationale: uvicorn is a high-performance ASGI server for FastAPI.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
