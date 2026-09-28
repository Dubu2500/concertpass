#!/bin/bash

aws rds create-db-instance \
  --db-instance-identifier ticket-checkout-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 16 \
  --allocated-storage 20 \
  --master-username ticket_checkout_admin \
  --manage-master-user-password \
  --backup-retention-period 7 \
  --no-publicly-accessible \
  --region us-east-1

aws rds wait db-instance-available \
  --db-instance-identifier ticket-checkout-db \
  --region us-east-1

echo "RDS instance is ready"

