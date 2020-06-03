import sys
import datetime
import config as cfg
import socket
from db_interface import DBInterface
from socket import error as SocketError
from user_exception import UserTimeoutException
from amazon_interface import AmazonInterface
from interface_server import InterfaceServer


def init_database():
    # warehouse, products, orders, local_storages, carts
    # miniamazon_app_localstorage_product, miniamazon_app_product_warehouse
    table_names = [
        'miniamazon_app_cart_product',
        'miniamazon_app_cart_warehouse',
        'miniamazon_app_cart',
        
        'miniamazon_app_localstorage_product',
        'miniamazon_app_localstorage',
        
        'miniamazon_app_product_order',
        'miniamazon_app_product_warehouse',
        'miniamazon_app_order_warehouse',
        'miniamazon_app_order',
        'miniamazon_app_ordercollection',
        'miniamazon_app_product',
        'miniamazon_app_warehouse',
    ]
    for table_name in table_names:
        db_command = 'DELETE FROM ' + table_name
        db_interface = DBInterface(cfg.db_name, cfg.db_user, cfg.db_password, cfg.db_host, cfg.db_port)
        db_interface.setup_excecute_and_close(db_command)


def init_warehouse(warehouse_data):
    for data in warehouse_data:
        db_command = 'INSERT INTO miniamazon_app_warehouse(warehouse_id, x, y) SELECT ' + \
            str(data['warehouse_id']) + ', ' + str(data['x']) + ', ' + str(data['y']) + \
            ' WHERE NOT EXISTS(select * from miniamazon_app_warehouse WHERE warehouse_id=' + \
            str(data['warehouse_id']) + ')'
        db_interface = DBInterface(cfg.db_name, cfg.db_user, cfg.db_password, cfg.db_host, cfg.db_port)
        db_interface.setup_excecute_and_close(db_command)


def first_purchase(recv_wrapper, seqnum):
    # construct a db command
    whnum = recv_wrapper.get_data().arrived[0].whnum
    product_id = recv_wrapper.get_data().arrived[0].things[0].id
    product_desc = recv_wrapper.get_data().arrived[0].things[0].description
    product_count = recv_wrapper.get_data().arrived[0].things[0].count
    
    db_command1 = 'INSERT INTO miniamazon_app_product(product_id, name, description, price, ' + \
        'storage) VALUES(' + str(product_id) + ', \'' + product_desc + \
        '\', \'' + product_desc + '\', ' + str(50) + ', ' + str(product_count) + ')' + \
        ' ON CONFLICT DO NOTHING'
    db_command2 = 'INSERT INTO miniamazon_app_product_warehouse(product_id, warehouse_id) VALUES(' + \
        str(product_id) + ', ' + str(whnum) + ')' + ' ON CONFLICT DO NOTHING'
    db_command3 = 'INSERT INTO miniamazon_app_localstorage(storage, warehouse_id) VALUES(' + str(product_count) + \
        ', ' + str(whnum) + ') ON CONFLICT DO NOTHING RETURNING local_storage_id'
    # update database
    db_interface = DBInterface(cfg.db_name, cfg.db_user, cfg.db_password, cfg.db_host, cfg.db_port)
    db_interface.setup_excecute_and_close(db_command1)
    db_interface.setup_excecute_and_close(db_command2)
    db_interface.setup()
    db_interface.execute(db_command3)
    local_storage_id = db_interface.cursor.fetchone()[0]
    db_interface.close()
    db_command4 = 'INSERT INTO miniamazon_app_localstorage_product(localstorage_id, product_id) ' + \
        'VALUES('+ str(local_storage_id) + ', ' + str(product_id) + ') ON CONFLICT DO NOTHING' 
    db_interface.setup_excecute_and_close(db_command4)


def setup_socket(interface, ups_or_world):
    start = datetime.datetime.now()
    while True:
        curr = datetime.datetime.now()
        duration = curr - start
        if duration.seconds > cfg.max_timeout:
            interface.close_socket()
            cfg.logger.debug('Cannot build socket: timeout.')
            cfg.logger.debug('Amazon interface server quit.')
            interface.close_socket()
            sys.exit()
        cfg.logger.info('Building socket.')
        try:  
            interface.build_socket()
        except SocketError as e:
            cfg.logger.debug('Cannot build socket: {}.'.format(e))
            continue
        cfg.logger.info('Socket build.')
        if ups_or_world == 'ups':
            cfg.logger.info('IP/Host Name: {}.'.format(cfg.ups_server_host))
            cfg.logger.info('Port: {}.'.format(cfg.ups_server_port))
        elif ups_or_world == 'world':
            cfg.logger.info('IP/Host Name: {}.'.format(cfg.world_simulator_host))
            cfg.logger.info('Port: {}.'.format(cfg.world_simulator_port))
        break


if __name__ == '__main__':
    amazon_ups = AmazonInterface(cfg.ups_server_host, cfg.ups_server_port)
    amazon_world = AmazonInterface(cfg.world_simulator_host, cfg.world_simulator_port)
    cfg.logger.info('Setting up Amazon UPS interface.')
    setup_socket(amazon_ups, 'ups')
    cfg.logger.info('Setting up Amazon world interface.')
    setup_socket(amazon_world, 'world')

    warehouse_data = list()
    for i in range(1):
        warehouse = dict()
        warehouse['warehouse_id'] = i + 1
        warehouse['x'], warehouse['y'] = 10*(i+1), 10*(i+1)
        warehouse_data.append(warehouse)

    cfg.logger.info('Initialize database.')
    init_database()

    seqnum = 0
    while True:
        try:
            # connect to the world, initialize warehouse id and position
            worldid = amazon_ups.get_world_id()
            cfg.logger.info('World ID: {}'.format(worldid))
            amazon_world.connect_to_world(warehouse_data, worldid)
            cfg.logger.info('Initialize warehouse.')
            init_warehouse(warehouse_data)
            # initialize stockpile of products
            product_ids = [1, 2, 3, 4, 5]
            product_names = ['apple', 'banana', 'orange', 'pineapple', 'strawberry']
            descriptions = product_names
            counts = [cfg.max_storage, cfg.max_storage, cfg.max_storage, cfg.max_storage, cfg.max_storage]
            for i in range(1):
                for j in range(cfg.num_products):
                    seqnum += 1
                    recv_wrapper = amazon_world.purchase_more(
                        i + 1, product_ids[j], descriptions[j], counts[j], seqnum)
                    first_purchase(recv_wrapper, seqnum)
        except UserTimeoutException as e:
            cfg.logger.debug('Error in connecting to world: {}.'.format(e))
            continue
        break

    # run interface server
    cfg.logger.info('Setting up Amazon interface server.')
    interface_server = InterfaceServer(cfg.interface_server_port, amazon_world, amazon_ups, seqnum)
    interface_server.build_socket()
    interface_server.runserver()
