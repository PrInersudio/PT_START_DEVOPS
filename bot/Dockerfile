FROM python:3.12.3-slim
WORKDIR /app
VOLUME ./db_logs
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "practice_bot.py"]