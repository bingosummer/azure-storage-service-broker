#!/bin/sh

# Build and run a service broker
cd ~/azure-storage-service-broker
cf push

# Create a service broker and make the service public
cf create-service-broker demo-service-broker $1 $2 http://azure-storage-service-broker.cf.azurelovecf.com
cf enable-service-access azurestorage
cf marketplace

# Build and run a demo app
cd ~/azure-storage-consumer
cf push azure-storage-consumer

# Create and bind the service instance
cf create-service azurestorage default myblobservice
cf bind-service azure-storage-consumer myblobservice
cf services
cf restart azure-storage-consumer
