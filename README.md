# concertpass

## Cómo correrlo (PDF 14, pasos 3 y 5)

1. Crear recursos y publicar imágenes:
```bash
   export AWS_PAGER=""
   export DB_PASSWORD='<password>'
   ./scripts/create-rds-instance.sh
   ./scripts/create-sqs.sh
   ./scripts/publish-ecr.sh ticket-api
   ./scripts/publish-ecr.sh ticket-worker
```

2. Variables (en cada terminal):
```bash
   ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   REGISTRY=$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
   DB_HOST=$(aws rds describe-db-instances --db-instance-identifier ticket-checkout-db --query "DBInstances[0].Endpoint.Address" --output text)
   SQS_HOST=$(aws sqs get-queue-url --queue-name concertpass-reservations.fifo --query QueueUrl --output text)
   AWS_KEYS="-e AWS_DEFAULT_REGION=us-east-1 -e AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id) -e AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key) -e AWS_SESSION_TOKEN=$(aws configure get aws_session_token)"
```

3. Terminal 1, ticket-api:
```bash
   docker run -p 8080:8080 -e DB_HOST=$DB_HOST -e DB_PORT=5432 -e DB_NAME=concertpass -e DB_USER=postgres -e DB_PASSWORD=<password> -e SQS_HOST=$SQS_HOST $AWS_KEYS $REGISTRY/ticket-api:latest
```

4. Terminal 2, ticket-worker:
```bash
   docker run -e SQS_HOST=$SQS_HOST $AWS_KEYS $REGISTRY/ticket-worker:latest
```

5. Terminal 3, probar:
```bash
   curl -X POST "http://localhost:8080/reserve" -H "Content-Type: application/json" -d '{"concert_id":"bad-bunny-gdl","user_id":"usr_123","ticket_type":"vip","quantity":2}'
```
   Responde `"status":"pending"` y el mensaje aparece en la consola de ticket-worker.

6. Limpiar: `./scripts/teardown.sh`
