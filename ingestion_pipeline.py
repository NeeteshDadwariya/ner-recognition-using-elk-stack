from kafka import KafkaProducer

import time
import datetime
import yaml
import json
import requests

with open('app-config.yml') as f:
    props = yaml.safe_load(f)

producer = None
api_key = props['api_key']
last_retrieval_time = None


def get_news_url():
    global last_retrieval_time

    url = props['news_api_url'].replace('{api_key}', api_key)
    if last_retrieval_time is None:
        return url
    time_obj = datetime.datetime.fromisoformat(last_retrieval_time)
    new_time_obj = time_obj + datetime.timedelta(seconds=1)
    new_time_str = new_time_obj.isoformat()
    return url + f"&from={new_time_str}"

def stream_news():
    global last_retrieval_time, producer

    try:
        url = get_news_url()
        print("Requesting URL:", url)
        response = requests.get(url).json()
        if response and response['status'] == 'ok' and len(response['articles']) > 0:
            last_retrieval_time = response['articles'][0]['publishedAt'][:-1]
            for article in response['articles']:
                title = article['title']
                desc = article['description']
                if producer is None:
                    producer = KafkaProducer(bootstrap_servers=props['bootstrap_servers'],
                                  value_serializer=lambda x: json.dumps(x).encode('utf-8'))
                kafka_data = {'title': title, 'desc': desc}
                print("Writing news to kafka:", json.dumps(kafka_data))
                producer.send(props['input_topic'], value=kafka_data)
        else:
            print("Unable to retrieve data from API:", response)
    except Exception as e:
        print(e)


while True:
    stream_news()
    time.sleep(int(props['news_api_request_delay']))

producer.close()
