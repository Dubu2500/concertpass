import os
import uuid
from datetime import datetime, timezone
import boto3
import json

import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="ticket-api")
sqs = boto3.client("sqs")
queue_url = os.environ["SQS_HOST"]

def get_connection():
    # Toda la configuración viene de variables de ambiente (nada hardcodeado)
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connect_timeout=5,
    )

class Reservation(BaseModel):
    concert_id: str
    user_id: str
    ticket_type: str
    quantity: int = Field(gt=0)

def send_reservation_message(reservation: dict):
    msg = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(reservation),
        MessageGroupId=reservation["concert_id"]
    )

    return msg["MessageId"]

@app.on_event("startup")
def create_table():
    # Crea la tabla reservations al iniciar la app (esquema de la diapositiva 48)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reservations (
                reservation_id UUID PRIMARY KEY,
                concert_id VARCHAR NOT NULL,
                user_id VARCHAR NOT NULL,
                ticket_type VARCHAR NOT NULL,
                quantity INTEGER NOT NULL,
                status VARCHAR NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );
            """
        )

@app.post("/reserve", status_code=201)
def reserve(req: Reservation):
    reservation_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO reservations
                    (reservation_id, concert_id, user_id, ticket_type,
                     quantity, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (reservation_id, req.concert_id, req.user_id, req.ticket_type,
                 req.quantity, "pending", now, now),
            )
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {e}")
    
    reservation = {
        "reservation_id": reservation_id,
        "concert_id": req.concert_id,
        "user_id": req.user_id,
        "ticket_type": req.ticket_type,
        "quantity": req.quantity,
        "status": "pending",
    }

    try:
        send_reservation_message(reservation)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enviando mensaje a SQS: {e}")

    return reservation