#!/bin/bash
# Borra todo lo que crea concertpass en AWS:
# - la cola SQS (PDF 14, paso 5)
# - los repositorios de ECR y la RDS con su tabla (PDF 13, diapositiva 47)
# No usa "set -e" para que siga aunque algo ya se haya borrado.

REGION=us-east-1
DB_ID=ticket-checkout-db
SG_NAME=concertpass-rds-sg

echo "== Borrando la cola SQS"
QUEUE_URL=$(aws sqs get-queue-url --queue-name concertpass-reservations.fifo \
  --query QueueUrl --output text --region $REGION)
aws sqs delete-queue --queue-url "$QUEUE_URL" --region $REGION

echo "== Borrando repositorios de ECR (--force borra también las imágenes)"
for repo in ticket-checkout ticket-api ticket-worker; do
  aws ecr delete-repository --repository-name $repo --force --region $REGION >/dev/null \
    && echo "Borrado: $repo"
done

echo "== Borrando la RDS (con ella se borra la tabla reservations)"
aws rds delete-db-instance --db-instance-identifier $DB_ID \
  --skip-final-snapshot --delete-automated-backups --region $REGION >/dev/null
echo "Esperando a que la RDS se borre (tarda varios minutos)..."
aws rds wait db-instance-deleted --db-instance-identifier $DB_ID --region $REGION

echo "== Borrando el security group de la RDS"
SG_ID=$(aws ec2 describe-security-groups --filters Name=group-name,Values=$SG_NAME \
  --query "SecurityGroups[0].GroupId" --output text --region $REGION)
aws ec2 delete-security-group --group-id $SG_ID --region $REGION

echo "Teardown completo"
