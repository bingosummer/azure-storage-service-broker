# Cloud Foundry Service Broker for Azure Storage

The broker currently publishes a single service and plan for provisioning Azure Storage containers. 

## Design

The broker uses meta data in Azure Storage and naming conventions to maintain the state of the services it is brokering. It does not maintain an internal database so it has no dependencies besides Azure Storage.

Capability with the Cloud Foundry service broker API is indicated by the project version number. For example, version 2.5.0 is based off the 2.5 version of the broker API.

## Running

Simply run `azurestorageservicebroker.py` and provide Azure Storage credentials via the `SUBSCRIPTION_ID`, `CERTIFICATE`, `AZURE_STORAGE_ACCOUNT` and `AZURE_ACCESS_KEY` environment variables.

### Locally

```
export AZURE_STORAGE_ACCOUNT="ACCOUNT-NAME"
export AZURE_ACCESS_KEY="ACCOUNT-KEY"
python azurestorageservicebroker.py
```

### In Cloud Foundry

Update manifest.yml with your credentials and push the broker to Cloud Foundry:
```
cf push
```

Create Cloud Foundry service broker:
```
cf create-service-broker demo-service-broker your-username-here your-password-here http://azure-storage-service-broker.cf.azurelovecf.com
```

Add service broker to Cloud Foundry Marketplace:
```
cf enable-service-access azurestorage
```

## Using the services in your application

### Format of Credentials

The credentials provided in a bind call have the following format:

```
"credentials":{
    "storage_account_name": "ACCOUNT-NAME",
    "storage_account_key": "ACCOUNT-KEY",
    "container_name":"cloud-foundry-2eac2d52-bfc9-4d0f-af28-c02187689d72"
}
```

### Bind the services
```
cf create-service azurestorage default myblobservice
cf bind-service azure-storage-consumer myblobservice
cf restart azure-storage-consumer
```

### Python Applications

For Python applications, you may consider using [Azure Storage Consumer](https://github.com/bingosummer/azure-storage-consumer).

## Creation and Naming of Azure Resources

A service provisioning call will create Azure Storage Account or Azure Storage Container. If you provides subscription id and certificate only, the provisioning will create a storage account (Classic) and a container in it. If you provides a prepared storage account, the provisioning will only create a container. A binding call will return credentials. Unbinding and deprovisioning calls will delete all resources created.

The following names are used and can be customized with a prefix:

Resource         | Name is based on     | Custom Prefix Environment Variable  | Default Prefix    | Example Name  
-----------------|----------------------|-------------------------------------|-------------------|---------------
Azure Storage Account | the first part of service instance ID | STORAGE_ACCOUNT_NAME_PREFIX | cfservicebroker | cfservicebroker2eac2d52
Azure Storage Containers | service instance ID | CONTAINER_NAME_PREFIX | cloud-foundry- | cloud-foundry-2eac2d52-bfc9-4d0f-af28-c02187689d72

## User for Broker

An Azure user and a storage account must be created for the broker. The user's storageName and storageKey must be provided using the environments variables `AZURE_STORAGE_ACCOUNT` and `AZURE_ACCESS_KEY`.

## Container Tagging

All containers are tagged with the following values:
* serviceInstanceId
* serviceDefinitionId
* planId
* organizationGuid
* spaceGuid

The ability to apply additional custom tags is in the works.

## Registering a Broker with the Cloud Controller

See [Managing Service Brokers](http://docs.cloudfoundry.org/services/managing-service-brokers.html).
