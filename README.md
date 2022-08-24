# KI-Campus Chatbot "KIM"

## Training of the Model 

Choose the folder with the chatbot in English (KI-Campus_en) or in German (KI-Campus_de)

```sh
    rasa train
```

## Usage

### Start the Rasa Server

```sh
    rasa run --enable-api
```

### Start the Action Server

```sh
    cd actions/
    rasa run actions
```

### Start for Development

Change configuration to _'for local development'_ endpoint in `endpoints.yml` in sub-directories
```
    rasa/KI-Campus_de/
    rasa/KI-Campus_en/
```

then (within the respective directory) start the chatbot shell with

```sh
    rasa shell
```

## Docker

In the outer project structure run:

### Docker Compose (de)

```sh
    docker-compose -f docker-compose_de.yml -p kicampus_de up --build
```

### Docker Compose (en)

```sh
    docker-compose -f docker-compose_en.yml -p kicampus_en up --build
```
