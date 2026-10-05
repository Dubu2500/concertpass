import json
import os
import time

import boto3

# La URL de la cola viene de variable de ambiente, igual que en ticket-api
QUEUE_URL = os.environ["SQS_HOST"]
sqs = boto3.client("sqs")

print(f"ticket-worker escuchando la cola: {QUEUE_URL}", flush=True)

try:
    while True:
        # 1. Polling: pide mensajes a la cola
        response = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=10,  # long polling: espera hasta 10 s a que llegue algo
        )

        for message in response.get("Messages", []):
            # 2. Imprime el mensaje
            reservation = json.loads(message["Body"])
            print(f"Mensaje recibido: {reservation}", flush=True)

            # 3. Lo borra de la cola para que no se vuelva a procesar
            sqs.delete_message(
                QueueUrl=QUEUE_URL,
                ReceiptHandle=message["ReceiptHandle"],
            )
            print(f"Mensaje {message['MessageId']} borrado de la cola", flush=True)

        # 4. Espera 5 segundos antes de volver a hacer polling
        time.sleep(5)
except KeyboardInterrupt:
    print("ticket-worker detenido", flush=True)
