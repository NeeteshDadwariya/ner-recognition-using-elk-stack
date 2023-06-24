## Spark Streaming with Real Time Data and Kafka and ELK stack

### How to run

The project is setup in docker-containerized environment and can be easily launched using 

`docker-compose up` 

All the configurations are present in `app-config.yml`

It will automatically download all the base images and will launch the necessary services. Docker daemon has to be running for it. Please see here or more details - https://docs.docker.com/compose/ 

Respective launched applications can be found at

•	Kafka - <localhost:9092> (Inside containers it will be accessible as <kafka:29092>)

•	Elasticsearch - http://localhost:9200/ 

•	Kibana - http://localhost:5601/ (Please import [‘export.ndjson’] file in kibana to import dashboard analysis.)
