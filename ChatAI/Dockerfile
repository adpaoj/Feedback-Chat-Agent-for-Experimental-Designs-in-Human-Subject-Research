FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Copy entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Command to run the application
CMD ["./entrypoint.sh"]
