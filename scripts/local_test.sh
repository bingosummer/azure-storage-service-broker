#!/bin/sh
http GET 127.0.0.1:5000/v2/catalog X-Broker-Api-Version:2.6
http PUT 127.0.0.1:5000/v2/service_instances/$1 X-Broker-Api-Version:2.6 service_id=1 plan_id=1 organization_guid=1 space_guid=1
http DELETE 127.0.0.1:5000/v2/service_instances/$1 X-Broker-Api-Version:2.6 service_id=1 plan_id=1
