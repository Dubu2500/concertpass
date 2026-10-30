#!/usr/bin/env bash

# crea una tabla de eventos en dynamodb

set -e

aws dynamodb create-table \
  --table-name Concerts \
  --attribute-definitions AttributeName=concert_id,AttributeType=S \
  --key-schema AttributeName=concert_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST >/dev/null

echo "Creando la tabla de DynamoDB..."
aws dynamodb wait table-exists --table-name Concerts

aws dynamodb put-item --table-name Concerts --item '{
  "concert_id": {"S": "bad-bunny-gdl"},
  "name":       {"S": "Bad Bunny Debi tirar más fotos"},
  "date":       {"S": "2026-11-15"},
  "recinto":    {"S": "Estadio Akron, GDL"},
  "capacity": {"M": {
    "floor":   {"N": "100"},
    "vip":     {"N": "50"},
    "general": {"N": "500"}
  }}
}'

aws dynamodb put-item --table-name Concerts --item '{
  "concert_id": {"S": "gorillaz-gdl"},
  "name":       {"S": "Gorillaz The Mountain Tour"},
  "date":       {"S": "2026-12-09"},
  "recinto":    {"S": "Coliseo GNP Seguros, GDL"},
  "capacity": {"M": {
    "floor":   {"N": "200"},
    "vip":     {"N": "100"},
    "general": {"N": "700"}
  }}
}'

echo "Listo. Tabla 'Concerts' de DynamoDB creada y poblada."