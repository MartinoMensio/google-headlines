FROM stevetech8/dockselpy

COPY . /app
WORKDIR /app
RUN pip3 install -r requirements.txt

CMD ["python3", "-m", "google_headlines", "periodic"]