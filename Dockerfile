FROM python
WORKDIR /
RUN pip install --upgrade pip
COPY requirements.txt requirements.txt
RUN pip install --upgrade setuptools
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y make
RUN chmod 755 .
COPY . .

CMD ["/bin/bash", "-c", "python bot/main.py"]