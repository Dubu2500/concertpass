#!/bin/bash

# despliega ticket-api y ticket-checkout en el cluster
# requiere kubectl y helm

set -e

REGION=us-east-1
DB_ID=ticket-checkout-db

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
SQS_QUEUE_URL=$(aws sqs get-queue-url --queue-name concertpass-reservations.fifo \
  --region $REGION --query QueueUrl --output text)
DB_HOST=$(aws rds describe-db-instances --db-instance-identifier $DB_ID \
  --query "DBInstances[0].Endpoint.Address" --output text --region $REGION)
DB_SECRET_ARN=$(aws rds describe-db-instances --db-instance-identifier $DB_ID \
  --query "DBInstances[0].MasterUserSecret.SecretArn" --output text --region $REGION)

aws eks update-kubeconfig --name concertpass-cluster --region $REGION

# instala External Secrets Operator para leer secrets manager
helm repo add external-secrets https://charts.external-secrets.io >/dev/null
helm repo update >/dev/null
helm upgrade --install external-secrets external-secrets/external-secrets \
  -n external-secrets --create-namespace --set installCRDs=true --wait

# referencia el secreto de Secrets Manager
sed -e "s|\${DB_HOST}|$DB_HOST|g" \
    -e "s|\${DB_SECRET_ARN}|$DB_SECRET_ARN|g" \
    k8s/external_secrets.yaml | kubectl apply -f -
kubectl wait --for=condition=Ready externalsecret/ticket-api-db --timeout=120s

# desplega los manifests
for APP in ticket-api ticket-checkout; do
  sed -e "s|\${ACCOUNT_ID}|$ACCOUNT_ID|g" \
      -e "s|\${SQS_QUEUE_URL}|$SQS_QUEUE_URL|g" \
      k8s/$APP.yaml | kubectl apply -f -
done

kubectl rollout status deployment/ticket-api --timeout=180s
kubectl rollout status deployment/ticket-checkout --timeout=180s
kubectl get pods
kubectl get services