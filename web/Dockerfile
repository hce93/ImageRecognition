FROM python:3
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN apt-get update && \
    apt-get install -y libhdf5-dev
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python","app.py"]