FROM python:3.10.8

ADD src/main.py .

COPY requirements.txt /tmp/requirements.txt
COPY . .

RUN pip install --no-cache-dir -r /tmp/requirements.txt
RUN pytest src/test.py

CMD ["python", "src/main.py"]
