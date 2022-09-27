# KI-Campus Chatbot "KIM"

## Training of the Model 

Choose the folder with the chatbot in English (KI-Campus_en) or in German (KI-Campus_de)

```sh
    rasa train
```

## Configuration

### Course Recommender Endpoint

> __NOTE__ Currently only supported for German chabot (`rasa/KI-Campus_de/`)

Create (or modify) the configuration file `kic_recommender.yml` in directory
```
    rasa/KI-Campus_de/
```

and add/modify configuration entry for Course Recommender Endpoint with the
base URL for the endpoint and the access token:
```yml
# This file contains the custom service endpoints your bot can use.

# recommender service (DFKI) configuration
recommender_api:
  url: "<base URL for recommender service endpoint>"
  token: "<recommender access token>"

```

## Usage

### Start the Rasa Server

```sh
    rasa run --enable-api
```

### Start the Action Server

```sh
    rasa run actions
```

NOTE the actions **must not** be started from within the `actions/` sub-directory, 
     but the `rasa` project's root directory (e.g. `rasa/KI-Campus_de/`),
     otherwise not all actions may be automatically started.

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
