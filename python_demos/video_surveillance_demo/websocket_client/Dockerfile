FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["sh", "-c", "python traffic_post_processor.py --server $WS_SERVER --camera-ids $CAMERA_IDS"]
