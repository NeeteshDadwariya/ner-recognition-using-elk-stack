from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

import spacy
import yaml

spark = SparkSession.builder.appName("StructuredKafkaWordCount1").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

with open('app-config.yml') as f:
    props = yaml.safe_load(f)

KAFKA_INPUT_TOPIC = props['input_topic']
KAFKA_OUTPUT_TOPIC = props['output_topic']
KAFKA_BOOTSTRAP_SERVER = props['bootstrap_servers']
CHECKPOINT_LOCATION = props['checkpoint_location']

spacy.cli.download('en_core_web_sm')
nlp = spacy.load("en_core_web_sm")

df = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVER)
        .option("subscribe", KAFKA_INPUT_TOPIC)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )

df = df.selectExpr("CAST(value as STRING)", "timestamp")
schema = (
        StructType()
        .add("title", StringType())
        .add("desc", StringType())
    )

news_df = df.select('timestamp',
                    from_json(col("value").cast("string"), schema).alias("parsed_value"))

def preprocessing(lines):
    lines = lines.select('timestamp',
                         lines.parsed_value.title.alias("text"))
    lines = lines.withColumn('text', lower(lines['text']))
    lines = lines.withColumn('text', regexp_replace(lines['text'], r'[^a-zA-Z0-9\s]', ''))
    lines = lines.withColumn('text', regexp_replace(lines['text'], '<.*?>', ''))
    lines = lines.withColumn('text', regexp_replace(lines['text'], r'\d+', ''))
    lines = lines.filter(lines.text.isNotNull())
    return lines

processed_df = preprocessing(news_df)

@udf(StringType())
def spacy_ner(text):
    doc = nlp(text)
    entities = []
    for token in doc.ents:
        entities += [token.text]
    print(f"NER entities {entities} for doc {doc}")
    return ' '.join(entities)

ner_df = processed_df.withColumn("named_entities", spacy_ner('text'))
ner_df = ner_df.withWatermark("timestamp", "10 seconds")

# Define the window duration and sliding interval
window_duration = "10 seconds"
sliding_interval = "10 seconds"

ner_count_df = ner_df.withColumn('word', explode(split(col('named_entities'), ' '))) \
    .filter("word is not null and word <> ''")\
    .groupBy('word', window("timestamp", window_duration, sliding_interval).alias('timestamp')).count()

query = ner_count_df.withColumn("value", to_json(struct('word', 'count'))).select("value")\
        .writeStream.trigger(processingTime="10 seconds")\
        .outputMode("append")\
        .format("kafka")\
        .option("topic", KAFKA_OUTPUT_TOPIC)\
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVER)\
        .option("checkpointLocation", CHECKPOINT_LOCATION)\
        .start()\
        .awaitTermination()

