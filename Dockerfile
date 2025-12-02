FROM python

WORKDIR /

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt

RUN pip install --upgrade pip && \
    pip install --upgrade setuptools && \
    pip install -r requirements.txt

RUN apt-get update && apt-get install -y make
RUN chmod 755 .
COPY . .

CMD ["/bin/bash", "-c", "python bot/main.py"]