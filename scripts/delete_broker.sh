#!/bin/sh
cf delete azure-storage-consumer -f -r
cf delete-service myblobservice -f
cf delete-service-broker demo-service-broker -f
cf delete azure-storage-service-broker -f -r
