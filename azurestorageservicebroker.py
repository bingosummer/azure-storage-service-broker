import os
import time
import json
from flask import Flask
from flask import jsonify, request, abort
from azure.storage import BlobService
from azure.servicemanagement import ServiceManagementService
from azure import WindowsAzureConflictError

import logging
from logging.handlers import RotatingFileHandler

# constant representing the API version supported
# keys off HEADER X-Broker-Api-Version from Cloud Controller
X_BROKER_API_VERSION = 2.5
X_BROKER_API_VERSION_NAME = 'X-Broker-Api-Version'

# prefix
STORAGE_ACCOUNT_NAME_PREFIX = 'cfservicebroker'
CONTAINER_NAME_PREFIX = 'cloud-foundry'

# environment variables
subscription_id = os.environ.get('SUBSCRIPTION_ID')
cert = os.environ.get('CERTIFICATE')
account_name = os.environ.get('AZURE_STORAGE_ACCOUNT')
account_key = os.environ.get('AZURE_ACCESS_KEY')

app = Flask(__name__)

catalog_conf = 'service.json'
with open(catalog_conf) as f:
    catalog_json = json.loads(f.read())

cert_file = 'mycert.pem'
if cert:
    with open(cert_file, 'w') as f:
        f.write(cert)

@app.route('/v2/catalog', methods=['GET'])
def catalog():
    """
    Return the catalog of services handled
    by this broker

    GET /v2/catalog:

    HEADER:
        X-Broker-Api-Version: <version>

    return:
        JSON document with details about the
        services offered through this broker
    """
    api_version = request.headers.get('X-Broker-Api-Version')
    if not api_version or float(api_version) < X_BROKER_API_VERSION:
        abort(409, "Missing or incompatible {0}. Expecting version {1} or later, actual {2}".format(X_BROKER_API_VERSION_NAME, X_BROKER_API_VERSION, api_version))
    return jsonify(catalog_json)


@app.route('/v2/service_instances/<instance_id>', methods=['PUT'])
def provision(instance_id):
    """
    Provision an instance of this service
    for the given org and space

    PUT /v2/service_instances/<instance_id>:
        <instance_id> is provided by the Cloud
          Controller and will be used for future
          requests to bind, unbind and deprovision

    BODY:
        {
          "service_id":        "<service-guid>",
          "plan_id":           "<plan-guid>",
          "organization_guid": "<org-guid>",
          "space_guid":        "<space-guid>"
        }

    return:
        JSON document with details about the
        services offered through this broker
    """
    if 'application/json' not in request.content_type:
        abort(415, 'Unsupported Content-Type: expecting application/json, actual {0}'.format(request.content_type))

    global subscription_id
    global cert
    global cert_file
    global account_name
    global account_key

    if subscription_id and cert and (not account_name):
        sms = ServiceManagementService(subscription_id, cert_file)
        name = '{0}{1}'.format(STORAGE_ACCOUNT_NAME_PREFIX, instance_id.split('-')[0])
        desc = name
        label = name
        location = 'West US'
        result = None
        try:
            result = sms.create_storage_account(name, desc, label, location=location)
        except WindowsAzureConflictError as e:
            pass
        if result:
            req_id = result.request_id
            operation = sms.get_operation_status(req_id)
            while operation.status == 'InProgress':
                time.sleep(5)
                operation = sms.get_operation_status(req_id)
                app.logger.info('Request ID: {0}, Operation Status: {1}'.format(req_id, operation.status))
            if operation.status == 'Succeeded':
                app.logger.info('Request ID: {0}, Operation Status: {1}'.format(req_id, operation.status))
                account_name = name
                account_key = sms.get_storage_account_keys(account_name).storage_service_keys.primary
                app.logger.info('Account Name: {0}, Account key: {1}'.format(account_name, account_key))

    if account_name:
        blob_service = BlobService(account_name, account_key)
        container_name = '{0}-{1}'.format(CONTAINER_NAME_PREFIX, instance_id)
        app.logger.info('Container Name: {0}'.format(container_name))
        request_body = request.get_json()
        if request_body.has_key('parameters'):
            parameters = request_body.pop('parameters')
        container_tags = request_body
        container_tags['instance_id'] = instance_id
        blob_service.create_container(
            container_name = container_name,
            x_ms_meta_name_values = container_tags)

    return jsonify({})


@app.route('/v2/service_instances/<instance_id>', methods=['DELETE'])
def deprovision(instance_id):
    """
    Deprovision an existing instance of this service

    DELETE /v2/service_instances/<instance_id>:
        <instance_id> is the Cloud Controller provided
          value used to provision the instance

    return:
        As of API 2.3, an empty JSON document
        is expected
    """
    global subscription_id
    global cert
    global account_name
    global account_key

    if account_name and account_key:
        blob_service = BlobService(account_name, account_key)
        container_name = '{0}-{1}'.format(CONTAINER_NAME_PREFIX, instance_id)
        blob_service.delete_container(container_name)

        if account_name.startswith(STORAGE_ACCOUNT_NAME_PREFIX):
            sms = ServiceManagementService(subscription_id, cert_file)
            sms.delete_storage_account(account_name)

    return jsonify({})


@app.route('/v2/service_instances/<instance_id>/service_bindings/<binding_id>', methods=['PUT'])
def bind(instance_id, binding_id):
    """
    Bind an existing instance with the
    for the given org and space

    PUT /v2/service_instances/<instance_id>/service_bindings/<binding_id>:
        <instance_id> is the Cloud Controller provided
          value used to provision the instance
        <binding_id> is provided by the Cloud Controller
          and will be used for future unbind requests

    BODY:
        {
          "plan_id":           "<plan-guid>",
          "service_id":        "<service-guid>",
          "app_guid":          "<app-guid>"
        }

    return:
        JSON document with credentails and access details
        for the service based on this binding
        http://docs.cloudfoundry.org/services/binding-credentials.html
    """
    if 'application/json' not in request.content_type:
        abort(415, 'Unsupported Content-Type: expecting application/json, actual {0}'.format(request.content_type))

    global subscription_id
    global cert
    global account_name
    global account_key

    container_name = '{0}-{1}'.format(CONTAINER_NAME_PREFIX, instance_id)

    return jsonify({
      "credentials": {
        "storage_account_name": account_name,
        "storage_account_key": account_key,
        "container_name": container_name
      }
    })

@app.route('/v2/service_instances/<instance_id>/service_bindings/<binding_id>', methods=['DELETE'])
def unbind(instance_id, binding_id):
    """
    Unbind an existing instance associated
    with the binding_id provided

    DELETE /v2/service_instances/<instance_id>/service_bindings/<binding_id>:
        <instance_id> is the Cloud Controller provided
          value used to provision the instance
        <binding_id> is the Cloud Controller provided
          value used to bind the instance

    return:
        As of API 2.3, an empty JSON document
        is expected
    """
    return jsonify({})


port = os.getenv('VCAP_APP_PORT', '5000')
if __name__ == "__main__":
    handler = RotatingFileHandler('broker.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.run(host='0.0.0.0', port=int(port), debug=True)
