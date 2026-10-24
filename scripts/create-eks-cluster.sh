#!/bin/bash

set -e

SG_NAME=concertpass-rds-sg
REGION=us-east-1
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
LAB_ROLE=arn:aws:iam::${ACCOUNT_ID}:role/LabRole

# AWS learner lab tiene un detalle, eksctl no puede crear los roles IAM porque el learner lab no te deja crear roles ni etiquetarlos
# por eso no podemos simplemente pegar el comando tal cual
# para solionarlo, modificamos el comando con la siguiente configuracion mediante stdin, mantenemos el nombre, region y los 2 worker nodes t3.medium
# pero tambien le asignamos el rol LabRole manualmente.
eksctl create cluster -f - <<EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: concertpass-cluster
  region: ${REGION}
iam:
  serviceRoleARN: ${LAB_ROLE}
managedNodeGroups:
  - name: workers
    instanceType: t3.medium
    desiredCapacity: 2
    iam:
      instanceRoleARN: ${LAB_ROLE}
EOF

SG_ID=$(aws ec2 describe-security-groups --region $REGION \
  --filters Name=group-name,Values=$SG_NAME \
  --query "SecurityGroups[0].GroupId" --output text)

# autoriza las ips en el puerto 5432
for IP in $(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="ExternalIP")].address}'); do
  aws ec2 authorize-security-group-ingress --group-id $SG_ID --region $REGION \
    --protocol tcp --port 5432 --cidr ${IP}/32 2>/dev/null || true
done