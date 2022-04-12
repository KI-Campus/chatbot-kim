FROM rasa/rasa:3.0.4-full
WORKDIR  '/app'
COPY . /app
USER root
RUN rasa train
VOLUME /app/models
CMD [ "run","-m","/app/models","--enable-api","--cors","*","--debug" ,"--endpoints", "endpoints.yml", "--log-file", "out.log", "--debug"]

EXPOSE 5005
