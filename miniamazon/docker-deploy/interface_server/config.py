import logging
import socket
import world_amazon_pb2 as wapb
from multiprocessing import Lock


# Logger
logger = logging.getLogger('amazon')
logger.setLevel(logging.DEBUG)

# psycopg2
db_name = 'postgres'
db_user = 'postgres'
db_password = ''
db_host = 'db'
db_port = '5432'

# db_name = 'amazondb'
# db_user = 'yijun'
# db_password = 'yijun'
# db_host = '127.0.0.1'
# db_port = '5432'

# UPS server
# ups_server_host = '67.159.88.97'
# ups_server_host = 'vcm-14675.vm.duke.edu'
ups_server_host = 'vcm-12233.vm.duke.edu'
# ups_server_host = 'vcm-12251.vm.duke.edu'
# ups_server_port = 7777
ups_server_port = 5000

# World simulator
# world_simulator_host = '152.3.69.133'
# world_simulator_host = 'vcm-14675.vm.duke.edu'
world_simulator_host = 'vcm-12233.vm.duke.edu'
# world_simulator_host = 'vcm-12251.vm.duke.edu'
world_simulator_port = 23456

# simulate_speed = 99999999

# Interface server
interface_server_port = 45678
process_capacity = 32
assert process_capacity > 0

# Max receive buffer length
max_buf_len = 65535

# Max storage
max_storage = 99999

# Max timeout in seconds
max_timeout = 10
max_blocking_time = 10

# Locks
# ps_lock = Lock()

# Number of products
num_products = 5
assert 1 <= num_products <= 5

# Protobuf lookup table
lookup_table = {
    'AInitWarehouse': wapb.AInitWarehouse,
    'AConnect': wapb.AConnect,
    'AConnected': wapb.AConnected,
    'APack': wapb.APack,
    'APacked': wapb.APacked,
    'ALoaded': wapb.ALoaded,
    'APutOnTruck': wapb.APutOnTruck,
    'APurchaseMore': wapb.APurchaseMore,
    'AErr': wapb.AErr,
    'AQuery': wapb.AQuery,
    'APackage': wapb.APackage,
    'ACommands': wapb.ACommands,
    'AResponses': wapb.AResponses,
    'UA_Connect': wapb.UA_Connect,
    'UA_TruckCall': wapb.UA_TruckCall,
    'UA_GoDeliver': wapb.UA_GoDeliver,
    'UA_TruckArrived': wapb.UA_TruckArrived,
    'UA_Delivered': wapb.UA_Delivered,
    'UA_Commands': wapb.UA_Commands,
    'UA_Responses': wapb.UA_Responses,
}


# def init_param(opt):
def init_param():
    global logger, start_time, curr_time, conn, \
        db_name, db_user, db_password, db_host, db_port, \
        world_simulator_host, world_simulator_port, \
        interface_server_port, process_capacity, max_buf_len, \
        max_storage, max_timeout, max_blocking_time, \
        lookup_table, ups_server_host, ups_server_port, \
        num_products

    # Set loggers
    fh = logging.FileHandler('./amazon.log', mode='w')
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(name)s] [%(levelname)s] %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)


init_param()
