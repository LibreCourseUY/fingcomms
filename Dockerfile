FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uvicorn

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
