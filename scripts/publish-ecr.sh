#!/bin/bash
# Construye y publica la imagen de un servicio en ECR
# (comandos de la diapositiva 49 del PDF 13).
#
# Uso, desde la raíz del repo:
#   ./scripts/publish-ecr.sh ticket-api
#   ./scripts/publish-ecr.sh ticket-checkout
#   ./scripts/publish-ecr.sh ticket-worker
set -e

SERVICE=$1
REGION=us-east-1

if [ -z "$SERVICE" ]; then
  echo "Uso: ./scripts/publish-ecr.sh <servicio>"
  exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGISTRY=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Crea el repositorio solo si no existe
aws ecr describe-repositories --repository-names $SERVICE --region $REGION >/dev/null 2>&1 || \
  aws ecr create-repository --repository-name $SERVICE --region $REGION

aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $REGISTRY

docker build -t $SERVICE apps/$SERVICE
docker tag $SERVICE:latest $REGISTRY/$SERVICE:latest
docker push $REGISTRY/$SERVICE:latest

echo "Imagen publicada: $REGISTRY/$SERVICE:latest"
