FROM rasa/rasa-sdk:3.2.1

WORKDIR /app

USER root

RUN pip install --no-cache-dir PyYAML==5.4.1

CMD ["start", "--actions", "actions", "--port", "5045"]
