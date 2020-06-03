import config as cfg
import datetime
import socket
import json
import world_amazon_pb2 as wapb
from copy import deepcopy
from multiprocessing import Process, Pool, Manager
from multiprocessing.pool import ThreadPool
from threading import Thread, ThreadError
from message_wrapper import MessageWrapper
from user_exception import UserKeyException
from db_interface import DBInterface


def get_order_status_from_sql(orderid, verbose=True):
        db_interface = DBInterface(cfg.db_name, cfg.db_user, cfg.db_password, cfg.db_host, cfg.db_port)
        db_command = 'SELECT status FROM miniamazon_app_ordercollection WHERE order_collection_id = ' + str(orderid) 
        db_interface.setup()
        db_interface.execute(db_command, verbose)
        status = db_interface.cursor.fetchone()[0]
        db_interface.close()
        return status

def get_truckid_from_sql(orderid, verbose=True):
    db_interface = DBInterface(cfg.db_name, cfg.db_user, cfg.db_password, cfg.db_host, cfg.db_port)
    db_command = 'SELECT truck_id FROM miniamazon_app_ordercollection WHERE order_collection_id = ' + str(orderid) 
    db_interface.setup()
    db_interface.execute(db_command, verbose)
    truck_id = db_interface.cursor.fetchone()[0]
    db_interface.close()
    return truck_id


class InterfaceServer:
    def __init__(self, port, amazon_world, amazon_ups, init_seqnum):
        self.port = port
        self.amazon_world = amazon_world
        self.amazon_ups = amazon_ups
        self.init_seqnum = init_seqnum
        self.socket = None
        
    def build_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', self.port))
        self.socket.listen(1)
        cfg.logger.info('Listen at {}:{}.'.format(socket.gethostname(), self.port))
        # self.socket.settimeout(cfg.max_blocking_time)

    def close_socket(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def restore_products(self, data, seqnum):
        assert self.amazon_world is not None
        keys = ['Warehouse ID', 'Product ID', 'Product Name', 'Amount To Purchase', 'Local Storage ID']
        for key in keys:
            if key not in data:
                raise UserKeyException('\"{}\" does not exist in restore_products data'.format(key))
        warehouse_ids = data['Warehouse ID']
        product_ids = data['Product ID']
        descriptions = data['Product Name']
        counts = data['Amount To Purchase']
        local_storage_ids = data['Local Storage ID']
        cfg.logger.info('Restore from warehouse.')
        assert len(warehouse_ids) == len(product_ids) == len(descriptions) == len(counts)
        for i in range(len(warehouse_ids)):
            self.amazon_world.purchase_more_send(
                warehouse_ids[i], product_ids[i], descriptions[i], counts[i], seqnum.value)
            db_command1 = 'UPDATE miniamazon_app_product SET storage = ' + str(cfg.max_storage) + \
                    ' WHERE product_id = ' + str(product_ids[i])
            db_command2 = 'UPDATE miniamazon_app_localstorage SET storage = ' + str(cfg.max_storage) + \
                ' WHERE local_storage_id = ' + str(local_storage_ids[i])
            db_interface = DBInterface(cfg.db_name, cfg.db_user, cfg.db_password, cfg.db_host, cfg.db_port)
            db_interface.setup_excecute_and_close(db_command1)
            db_interface.setup_excecute_and_close(db_command2)
            seqnum.value += 1

    def call_truck(self, data, seqnum):
        assert self.amazon_ups is not None
        package_id = data['Package ID']
        warehouse_id = data['Warehouse ID']
        product_ids = data['Product ID']
        descriptions = data['Product Description']
        counts = data['Count']
        owner = data['Owner']
        # dest_x = data['Delivery x']
        # dest_y = data['Delivery y']
        dest_x = [10]
        dest_y = [10]
        assert len(package_id) == len(warehouse_id) == len(dest_x) == len(dest_y) == 1
        
        self.amazon_ups.call_truck_send(
            package_id[0], 
            warehouse_id[0], 
            product_ids, 
            descriptions, 
            counts, 
            owner[0], 
            dest_x[0], 
            dest_y[0], 
            seqnum.value)

    def packing(self, data, seqnum):
        # warehouse_id, product_id, description, count, shipid, seqnum
        assert self.amazon_world is not None
        warehouse_id = data['Warehouse ID']
        product_ids = data['Product ID']
        descriptions = data['Product Description']
        counts = data['Count']
        shipid = data['Package ID']
        assert len(warehouse_id) == len(shipid) == 1
        assert len(product_ids) == len(descriptions) == len(counts)
        try:
            self.amazon_world.packing_send(warehouse_id[0], product_ids, descriptions, counts, shipid[0], seqnum.value)
        except KeyError as e:
            cfg.logger.debug('KeyError: {}.'.format(e))

    def put_on_truck(self, data, seqnum):
        assert self.amazon_world is not None
        warehouse_id = data['Warehouse ID']
        shipid = data['Package ID']
        truckid = get_truckid_from_sql(shipid[0])
        assert truckid is not None
        try:
            self.amazon_world.put_on_truck_send(warehouse_id[0], int(truckid), shipid[0], seqnum.value)
        except KeyError as e:
            cfg.logger.debug('KeyError: {}.'.format(e))

    def go_deliver(self, data, seqnum):
        assert self.amazon_ups is not None
        shipid = data['Package ID']
        truckid = get_truckid_from_sql(shipid[0])
        assert truckid is not None
        package_id = data['Package ID']
        dest_x = data['Delivery x']
        dest_y = data['Delivery y']
        try:
            self.amazon_ups.go_deliver_send(int(truckid), package_id[0], dest_x[0], dest_y[0], seqnum.value)
        except KeyError as e:
            cfg.logger.debug('KeyError: {}.'.format(e))

    def wait(self, key, sigs):
        if len(sigs) == 2:
            sig_status, sig_truck = sigs  # sig_truck could be any variable that is not None
            while True:
                status = get_order_status_from_sql(key, False)
                truck_id = get_truckid_from_sql(key, False)
                if status.lower() == sig_status.lower() and truck_id is not None:
                    break
                # if status == sig_status:
                #     break

        elif len(sigs) == 1:
            sig_status = sigs[0]
            while True:
                status = get_order_status_from_sql(key, False)
                if status.lower() == sig_status.lower():
                    break

    def handler(self, conn, packages_data, seqnum):
        assert self.socket is not None
        recv_msg = conn.recv(cfg.max_buf_len)
        if recv_msg: 
            recv_msg = recv_msg.decode('utf-8')
            cfg.logger.info('Received from Django: {}.'.format(recv_msg))

            json_data = json.loads(recv_msg)
            if 'Cart ID' in json_data:
                send_data = dict()
                send_data['acks'] = json_data['Cart ID']
                send_msg = json.dumps(send_data)
                conn.send(send_msg.encode('utf-8'))
                seqnum.value += 1
                try:
                    self.restore_products(json_data, seqnum)
                except UserKeyException as e:
                    cfg.logger.debug('Error: {}.'.format(e))
            elif 'Package ID' in json_data:
                send_data = dict()
                send_data['acks'] = json_data['Package ID']
                send_msg = json.dumps(send_data)
                conn.send(send_msg.encode('utf-8'))
                key = json_data['Package ID'][0]

                seqnum.value += 1
                packages_data[key] = json_data
                self.packing(packages_data[key], seqnum)
                self.call_truck(packages_data[key], seqnum)
                self.wait(key, sigs=('PACKED', 'Truck'))
                cfg.logger.info('Packed {}.'.format(key))
                
                seqnum.value += 1
                self.put_on_truck(packages_data[key], seqnum)
                self.wait(key, sigs=('LOADED',))
                cfg.logger.info('Loaded {}.'.format(key))
                
                seqnum.value += 1
                self.go_deliver(packages_data[key], seqnum)
                self.wait(key, sigs=('DELIVERED',))
                cfg.logger.info('Delivered {}.'.format(key))
                packages_data.pop(key, None)

    def handle_request(self, queue, packages_data, seqnum):
        assert self.socket is not None
        with Pool(processes=cfg.process_capacity) as pool:
            while True:
                conn = queue.get()
                pool.apply_async(self.handler, args=(conn, packages_data, seqnum))

    def runserver(self):
        try:
            assert self.socket is not None
            assert self.amazon_world is not None
            assert self.amazon_ups is not None
            packages_data = Manager().dict()
            queue = Manager().Queue()
            response_queue = Manager().Queue()
            seqnum = Manager().Value('i', self.init_seqnum)
            Process(target=self.handle_request, args=(queue, packages_data, seqnum)).start()
            cfg.logger.info('Triggered handle_request process.')
            Process(target=self.amazon_world.handle_responses, args=(response_queue, packages_data)).start()
            cfg.logger.info('Triggered handle_responses process.')
            Process(target=self.amazon_world.recv, args=('AResponses', response_queue)).start()
            cfg.logger.info('Triggered recv (AResponses) process.')
            Process(target=self.amazon_ups.recv, args=('UA_Responses', response_queue)).start()
            cfg.logger.info('Triggered recv (UA_Responses) process.')
            while True:
                conn, addr = self.socket.accept()
                seqnum.value += 1
                cfg.logger.info('Received a request from %s:%s.' % (*addr,))
                queue.put(conn)
                conn.close()
                del conn
        except KeyboardInterrupt as e:
            self.close_socket()
            cfg.logger.info('Program stops')
        except BrokenPipeError as e:
            self.close_socket()
            cfg.logger.info('Program stops')