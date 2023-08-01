FROM python:3.10

COPY ./requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY ./dropbox_langchain/ ./dropbox_langchain/
COPY ./dropbox-test.py .

CMD [ "python", "./dropbox-test.py" ]
