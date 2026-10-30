import json
import os
import signal
import time

import boto3
import psycopg2
import requests

QUEUE_URL = os.environ["SQS_HOST"]
TABLE_NAME = os.environ["DYNAMODB_TABLE"]
CHECKOUT_URL = os.environ["CHECKOUT_URL"].rstrip("/")

sqs = boto3.client("sqs")
concerts_table = boto3.resource("dynamodb").Table(TABLE_NAME)

running = True
_conn = None

# DynamoDB es de solo lectura en runtime, asi que se puede cachear la capacidad
_capacity_cache = {}

def get_conn():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(
            host=os.environ["DB_HOST"],
            port=os.environ.get("DB_PORT", "5432"),
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            connect_timeout=5,
        )
    return _conn


def reset_conn():
    global _conn
    try:
        if _conn is not None:
            _conn.close()
    except Exception:
        pass
    _conn = None

def fetch_reservation(conn, reservation_id):
    with conn, conn.cursor() as cur:
        cur.execute(
            "SELECT concert_id, ticket_type, quantity, status "
            "FROM reservations WHERE reservation_id = %s",
            (reservation_id,),
        )
        return cur.fetchone()

def set_status(conn, reservation_id, status):
    with conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE reservations SET status = %s, "
            "updated_at = NOW() AT TIME ZONE 'UTC' WHERE reservation_id = %s",
            (status, reservation_id),
        )

def try_book(conn, reservation_id, concert_id, ticket_type, quantity, capacity):
    #transaccion de inventario, true si hubo espacio y quedo "booked".

    # PostgreSQL no permite FOR UPDATE junto con SUM() (error "FOR UPDATE is not allowed with aggregate functions")
    # Por eso se usa un advisory lock transaccional por concierto y tipo de boleto. estandariza
    # la lectura, decision y escritura entre todos los workers y se libera solo con COMMIT/ROLLBACK.
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))",
                (f"{concert_id}:{ticket_type}",),
            )
            cur.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM reservations "
                "WHERE concert_id = %s AND ticket_type = %s "
                "AND status IN ('booked', 'confirmed')",
                (concert_id, ticket_type),
            )
            sold = int(cur.fetchone()[0])

            if sold + quantity > capacity:
                conn.rollback()  # no hay espacio: libera el lock sin escribir nada
                return False

            cur.execute(
                "UPDATE reservations SET status = 'booked', "
                "updated_at = NOW() AT TIME ZONE 'UTC' WHERE reservation_id = %s",
                (reservation_id,),
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise

def get_capacity(concert_id):
    # dict {tipo: capacidad} del concierto, o none si no existe.
    if concert_id in _capacity_cache:
        return _capacity_cache[concert_id]
    item = concerts_table.get_item(Key={"concert_id": concert_id}).get("Item")
    if item is None:
        return None
    capacity = {k: int(v) for k, v in item["capacity"].items()}
    _capacity_cache[concert_id] = capacity
    return capacity

def process(message):
    # procesa un mensaje. si regresa normal, el mensaje se borra de SQS. si lanza excepcion, no se borra y SQS lo reentrega
    try:
        reservation_id = json.loads(message["Body"])["reservation_id"]
    except (ValueError, KeyError, TypeError):
        print(f"Mensaje malformado, se descarta: {message.get('Body')}")
        return

    conn = get_conn()
    row = fetch_reservation(conn, reservation_id)
    if row is None:
        print(f"[{reservation_id}] no existe en RDS, se descarta")
        return

    concert_id, ticket_type, quantity, status = row

    if status in ("confirmed", "rejected"):
        print(f"[{reservation_id}] ya estaba {status}, no se hace nada")
        return

    if status == "pending":
        capacity = get_capacity(concert_id)
        limit = capacity.get(ticket_type) if capacity else None
        if limit is None:
            print(f"[{reservation_id}] concierto/tipo invalido ({concert_id}/{ticket_type}) -> rejected")
            set_status(conn, reservation_id, "rejected")
            return

        if try_book(conn, reservation_id, concert_id, ticket_type, quantity, limit):
            print(f"[{reservation_id}] {concert_id}/{ticket_type} x{quantity} -> booked")
        else:
            # transacción aparte, como pide el enunciado
            set_status(conn, reservation_id, "rejected")
            print(f"[{reservation_id}] {concert_id}/{ticket_type} x{quantity} sin espacio -> rejected")
            return

    # status == 'booked' (recien reservada o reintento tras un fallo de checkout)
    resp = requests.post(
        f"{CHECKOUT_URL}/checkout",
        json={"reservation_id": reservation_id, "quantity": quantity},
        timeout=5,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"checkout respondio {resp.status_code}")
    set_status(conn, reservation_id, "confirmed")
    print(f"[{reservation_id}] -> confirmed")

def main():
    print(f"ticket-worker escuchando la cola: {QUEUE_URL}")
    while running:
        try:
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=10,  # long polling
                AttributeNames=["MessageGroupId"],
            )
        except Exception as e:
            print(f"Error leyendo de SQS: {e}")
            time.sleep(2)
            continue

        # si falla un mensaje, los siguientes del mismo grupo se saltan y SQS los reentrega.
        failed_groups = set()
        for message in response.get("Messages", []):
            group = message.get("Attributes", {}).get("MessageGroupId")
            if group in failed_groups:
                continue
            try:
                process(message)
                sqs.delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=message["ReceiptHandle"],
                )
            except Exception as e:
                print(f"Error procesando {message.get('MessageId')}: {e!r} (se reintentará)")
                failed_groups.add(group)
                if isinstance(e, (psycopg2.OperationalError, psycopg2.InterfaceError)):
                    reset_conn()

    reset_conn()
    print("ticket-worker detenido")

if __name__ == "__main__":
    main()