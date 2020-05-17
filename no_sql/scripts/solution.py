from __future__ import print_function

import sys
import traceback
import aerospike
import logging
from aerospike import exception as ex
from aerospike import predicates as p

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)


def make_aerospike_client(config):
    try:
        return aerospike.client(config).connect()
    except ex.ClientError as e:
        exc = ' '.join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
        logging.error(f'failed to connect to the cluster with {config["hosts"]} and get exception {exc}')
        sys.exit(1)


def add_customer(client, ns, set, customer_id, record, policy=None, meta=None):
    if policy is None:
        policy = {'key': aerospike.POLICY_KEY_SEND}
    if meta is None:
        meta = {'ttl': 180}
    try:
        client.put((ns, set, customer_id), record, policy, meta)
    except ex.AerospikeError as e:
        exc = ' '.join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
        logging.error(f'error: {exc}')


def get_ltv_by_id(client, ns, set, customer_id, ltv_attr):
    try:
        (key, meta, records) = client.get((ns, set, customer_id))
        return records[ltv_attr]
    except ex.AerospikeError as e:
        logging.error(f'Requested non-existent customer {customer_id}')
        return None


def get_ltv_by_phone(client, ns, set, phone_field, ltv_field, phone_number, total_timeout=None):
    if total_timeout is None:
        total_timeout = {'total_timeout': 2000}
    query = client.query(ns, set) \
        .where(p.equals(phone_field, phone_number))
    return [record[2].get(ltv_field) for record in query.results(total_timeout)]


ns = 'test'
set = 'no_sql_dg'
config = {
    'hosts': [('db', 3000)],
    'total_timeout': 1500
}
phone_index = 'phone_index'
client = make_aerospike_client(config)
try:
    customer_id = 1
    phone_attr = 'phone'
    ltv_attr = 'ltv'
    phone_number_value = 7777777
    ltv_attr_value = 2754
    record = {
        phone_attr: phone_number_value,
        ltv_attr: ltv_attr_value
    }
    add_customer(client, ns, set, customer_id, record)
    client.index_integer_create(ns, set, phone_attr, phone_index)
    assert (get_ltv_by_id(client, ns, set, customer_id, ltv_attr) == record[ltv_attr])
    assert (get_ltv_by_id(client, ns, set, 77, ltv_attr) is None)
    assert (len(get_ltv_by_phone(client, ns, set, phone_attr, ltv_attr, phone_number_value)) == 1)
    logging.info('all tests passed')
except ex.AerospikeError as e:
    logging.error(f'Error: {e.msg} [{e.code}]')
    sys.exit(1)
finally:
    client.index_remove(ns, phone_index)
    client.close()
