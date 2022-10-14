FROM rasa/rasa:3.2.5-full
WORKDIR  '/app'
COPY . /app
USER root
#RUN python -m spacy download en_core_news_md --no-cache-dir
RUN rasa train
VOLUME /app/models
CMD [ "run","-m","/app/models","--enable-api","--cors","*","--debug" ,"--endpoints", "endpoints_docker.yml", "--log-file", "out.log", "--debug"]

EXPOSE 5005
