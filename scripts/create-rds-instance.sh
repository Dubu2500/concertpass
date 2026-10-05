#!/bin/bash
# Crea la RDS Postgres de concertpass.
# Debe ser pública y aceptar el puerto 5432 para que el contenedor
# en la laptop se pueda conectar (diapositiva 51 del PDF 13).
#
# Uso:
#   export DB_PASSWORD='tu-password'
#   ./scripts/create-rds-instance.sh
set -e

REGION=us-east-1
DB_ID=ticket-checkout-db
SG_NAME=concertpass-rds-sg

if [ -z "$DB_PASSWORD" ]; then
  echo "Primero define la contraseña: export DB_PASSWORD='...'"
  exit 1
fi

# VPC por defecto de la cuenta
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true \
  --query "Vpcs[0].VpcId" --output text --region $REGION)

# Security group que permite el puerto 5432 solo desde tu IP
SG_ID=$(aws ec2 create-security-group --group-name $SG_NAME \
  --description "Postgres de concertpass" --vpc-id $VPC_ID \
  --query GroupId --output text --region $REGION)

MY_IP=$(curl -s https://checkip.amazonaws.com)
aws ec2 authorize-security-group-ingress --group-id $SG_ID \
  --protocol tcp --port 5432 --cidr ${MY_IP}/32 --region $REGION

aws rds create-db-instance \
  --db-instance-identifier $DB_ID \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 16 \
  --allocated-storage 20 \
  --db-name concertpass \
  --master-username postgres \
  --master-user-password "$DB_PASSWORD" \
  --vpc-security-group-ids $SG_ID \
  --backup-retention-period 0 \
  --publicly-accessible \
  --region $REGION

echo "Esperando a que la RDS esté disponible (tarda varios minutos)..."
aws rds wait db-instance-available --db-instance-identifier $DB_ID --region $REGION

echo "RDS lista. Endpoint (DB_HOST):"
aws rds describe-db-instances --db-instance-identifier $DB_ID \
  --query "DBInstances[0].Endpoint.Address" --output text --region $REGION
