import datetime
import config as cfg
import world_amazon_pb2 as wapb
import socket
import argparse
import struct
import sys
from interface_server import get_order_status_from_sql, get_truckid_from_sql
from multiprocessing import Pool
from threading import Thread, ThreadError
from db_interface import DBInterface
from message_wrapper import MessageWrapper
from user_exception import UserTimeoutException
from google.protobuf.message import DecodeError
from google.protobuf.internal.decoder import _DecodeVarint32
from google.protobuf.internal.encoder import _EncodeVarint
from socket import error as SocketError
import psycopg2 as pg2

# define sequence number as a class variable, self increment in each method that builds a command
class AmazonInterface:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None

    def build_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.socket.settimeout(cfg.max_blocking_time)

    def close_socket(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def communicate(self, send_wrapper, cmd_key, seqnum_check=None):
        assert self.socket is not None
        recv_wrapper = MessageWrapper('')
        while True:
            # sending
            try:
                send_wrapper.encode_and_send(self.socket)
            except SocketError as e:
                if not seqnum_check:
                    cfg.logger.debug('Error in send: {}.'.format(e))
                else:
                    cfg.logger.debug('Error in send: {}.'.format(e))
                continue

            # receiving
            try:
                cmd_type = cfg.lookup_table[cmd_key]
                recv_wrapper.recv_and_parse(self.socket, cmd_type)
            except socket.timeout as e:
                # cfg.logger.debug('Timeout.')
                continue
            except SocketError as e:
                cfg.logger.debug('Error in receive: {}.'.format(e))
                continue
            except DecodeError as e:
                cfg.logger.debug('Error in decoding: {}'.format())
                continue
            except IndexError as e:
                # pass
                cfg.logger.debug('IndexError in recv_and_parse _DecodeVariant32: {}'.format(e))
                continue
        
            if recv_wrapper.get_message():
                if cmd_key != 'AResponses' and cmd_key != 'UA_Responses':
                    break
                else:
                    assert seqnum_check is not None
                    acks = recv_wrapper.get_data().acks
                    if acks and seqnum_check == acks[0]:
                        break

        return recv_wrapper

    def send(self, send_wrapper):
        assert self.socket is not None
        for _ in range(10):
            # sending
            try:
                send_wrapper.encode_and_send(self.socket)
            except SocketError as e:
                if seqnum_check is None:
                    cfg.logger.debug('Error in send: {}.'.format(e))
                else:
                    cfg.logger.debug('Error in send: {}.'.format(e))

    def send_ups(self, send_wrapper):
        assert self.socket is not None
        for _ in range(1):
            # sending
            try:
                send_wrapper.encode_and_send(self.socket)
            except SocketError as e:
                if seqnum_check is None:
                    cfg.logger.debug('Error in send: {}.'.format(e))
                else:
                    cfg.logger.debug('Error in send: {}.'.format(e))

    def recv(self, cmd_key, response_queue):
        assert self.socket is not None
        assert cmd_key == 'AResponses' or cmd_key == 'UA_Responses'
        recv_wrapper = MessageWrapper('')
        while True:
            # receiving
            try:
                cmd_type = cfg.lookup_table[cmd_key]
                recv_wrapper.recv_and_parse(self.socket, cmd_type)
            except socket.timeout as e:
                # cfg.logger.debug('Timeout.')
                continue
            except SocketError as e:
                cfg.logger.debug('Error in receive: {}.'.format(e))
                continue
            except DecodeError as e:
                cfg.logger.debug('Error in decoding: {}'.format())
                continue
            except IndexError as e:
                # pass
                cfg.logger.debug('IndexError in recv_and_parse _DecodeVariant32: {}'.format(e))
                cfg.logger.debug('Stop receiving! Please re-start the backend.')
                sys.exit()
                break
        
            if recv_wrapper.get_message():
                cfg.logger.info('Received: {}'.format(recv_wrapper.get_data()))
                if cmd_key == 'AResponses':
                    if recv_wrapper.get_data().arrived or recv_wrapper.get_data().ready or recv_wrapper.get_data().loaded:
                        response_queue.put((cmd_key, recv_wrapper))
                else:
                    response_queue.put((cmd_key, recv_wrapper))

        return recv_wrapper

    def handler(self, resp, packages_data):
        cmd_key, recv_wrapper = resp
        if cmd_key == 'AResponses':
            if recv_wrapper.get_data().arrived:
                self.purchase_more_recv(recv_wrapper)
            if recv_wrapper.get_data().ready:
                self.packing_recv(recv_wrapper, packages_data)
            if recv_wrapper.get_data().loaded:
                self.put_on_truck_recv(recv_wrapper, packages_data)
        else:
            if recv_wrapper.get_data().truckArrived:
                self.call_truck_recv(recv_wrapper, packages_data)  # handle with truckarrived response
            if recv_wrapper.get_data().delivered:
                self.go_deliver_recv(recv_wrapper, packages_data)
    
    def handle_responses(self, response_queue, packages_data):
        while True:
            # if response_queue:
            #     resp = response_queue.get()
            #     Thread(target=self.handler, args=(resp, packages_data)).start()
            with Pool(processes=cfg.process_capacity) as pool:
                while True:
                    resp = response_queue.get()
                    pool.apply_async(self.handler, args=(resp, packages_data))

    def get_world_id(self):
        assert self.socket is not None
        recv_wrapper = MessageWrapper('')
        start = datetime.datetime.now()
        while True:
            curr = datetime.datetime.now()
            duration = curr - start
            if duration.seconds > cfg.max_timeout:
                raise UserTimeoutException('timeout')
            try:
                recv_wrapper.recv_and_parse(self.socket, wapb.UA_Connect)
            except SocketError as e:
                cfg.logger.debug('Error in receive: {}.'.format(e))
                continue
            if recv_wrapper.get_message():
                break

        return recv_wrapper.get_data().worldid

    # arguments: product ID, description, count
    def prepare_product(self, product_id, description, count):
        # print(product_id, description, count)
        product = wapb.AProduct()
        product.id = product_id
        product.description = description
        product.count = count
        return product

    def create_connection_msg(self, warehouse_data, worldid):
        # CONNECT 
        connect = wapb.AConnect()
        if worldid is not None:
            connect.worldid = worldid
        connect.isAmazon = True
        for data in warehouse_data:
            warehouse = wapb.AInitWarehouse()
            warehouse.id = data['warehouse_id']
            warehouse.x, warehouse.y = data['x'], data['y']
            connect.initwh.append(warehouse)
        assert len(connect.initwh) == 1
        # connect.worldid = 2   
        data = connect.SerializeToString()
        connect_send = data
        # print("Message to send is: {}".format(connect_send))
        return connect_send

    def create_purchase_more_msg(self, warehouse_id, product_id, description, count, seqnum):
        product = self.prepare_product(product_id, description, count)
        purchase = wapb.APurchaseMore()
        purchase.whnum = warehouse_id
        purchase.things.append(product)
        purchase.seqnum = seqnum

        command = wapb.ACommands()
        command.buy.append(purchase)
        # command.simspeed = cfg.simulate_speed
        data_msg = command.SerializeToString()
        return data_msg

    # ack response from Amazon server to the world
    def create_acks_msg(self, acks):
        command = wapb.ACommands()
        command.acks.append(acks)
        
        data_msg = command.SerializeToString()
        return data_msg

    def create_acks_msg_in_batch(self, field):
        command = wapb.ACommands()
        for i in range(len(field)):
            command.acks.append(field[i].seqnum)
        
        data_msg = command.SerializeToString()
        return data_msg

    def create_truck_call_msg(self, package_id, warehouse_id, product_ids, descriptions, counts, 
    owner, dest_x, dest_y, seqnum):
        truck_call = wapb.UA_TruckCall()
        truck_call.package_id = package_id
        truck_call.whnum = warehouse_id

        for i in range(len(product_ids)):
            product = self.prepare_product(product_ids[i], descriptions[i], counts[i])
            truck_call.products.append(product)

        truck_call.owner_id = owner
        truck_call.dest_x = dest_x
        truck_call.dest_y = dest_y
        truck_call.seqnum = seqnum
        command = wapb.UA_Commands()
        command.truckCall.append(truck_call)
        command.acks.append(seqnum)
        data_msg = command.SerializeToString()

        return data_msg

    def create_pack_msg(self, warehouse_id, product_ids, descriptions, counts, shipid, seqnum):
        assert len(product_ids) == len(descriptions) == len(counts)
        pack = wapb.APack()
        pack.whnum = warehouse_id
        
        for i in range(len(product_ids)):
            product = self.prepare_product(product_ids[i], descriptions[i], counts[i])
            pack.things.append(product)

        pack.shipid = shipid
        pack.seqnum = seqnum

        command = wapb.ACommands()
        command.topack.append(pack)
        # command.simspeed = cfg.simulate_speed
        data_msg = command.SerializeToString()
        return data_msg

    def create_put_on_truck_msg(self, warehouse_id, truckid, shipid, seqnum):
        put_on_truck_msg = wapb.APutOnTruck()
        put_on_truck_msg.whnum = warehouse_id
        put_on_truck_msg.truckid = truckid
        put_on_truck_msg.shipid = shipid
        put_on_truck_msg.seqnum = seqnum

        command = wapb.ACommands()
        command.load.append(put_on_truck_msg)
        # command.simspeed = cfg.simulate_speed
        data_msg = command.SerializeToString()
        return data_msg

    def create_go_deliver_msg(self, truckid, package_id, dest_x, dest_y, seqnum):
        go_deliver_msg = wapb.UA_GoDeliver()
        go_deliver_msg.truckid = truckid
        go_deliver_msg.packageid = package_id
        go_deliver_msg.x = dest_x
        go_deliver_msg.y = dest_y
        go_deliver_msg.seqnum = seqnum
        
        command = wapb.UA_Commands()
        command.goDeliver.append(go_deliver_msg)
        command.acks.append(seqnum)
        data_msg = command.SerializeToString()
        
        return data_msg

    # build connection with world initially
    def connect_to_world(self, warehouse_data, worldid=None):
        send_wrapper = MessageWrapper(self.create_connection_msg(warehouse_data, worldid))
        recv_wrapper = self.communicate(send_wrapper, 'AConnected')
        cfg.logger.info('Received from warehouse: \n{}'.format(recv_wrapper.get_data()))

        # Consider sending acks
        return recv_wrapper

    # purchase products
    def purchase_more(self, warehouse_id, product_id, description, count, seqnum):
        send_wrapper = MessageWrapper(self.create_purchase_more_msg(warehouse_id, product_id, description, count, seqnum))
        cfg.logger.info('Purchase more.')
        recv_wrapper = self.communicate(send_wrapper, 'AResponses', seqnum)
        cfg.logger.info('Received from warehouse: \n{}'.format(recv_wrapper.get_data()))
        acks = recv_wrapper.get_data().acks
        # check if acks from response matches seqnum
        if seqnum == acks[0]:
            # send ack back to world
            world_seqnum = recv_wrapper.get_data().arrived[0].seqnum
            cfg.logger.info('Send acks: {}'.format(world_seqnum))
            ack_wrapper = MessageWrapper(self.create_acks_msg(world_seqnum))
            ack_wrapper.encode_and_send(self.socket)

        return recv_wrapper

    def purchase_more_send(self, warehouse_id, product_id, description, count, seqnum):
        send_wrapper = MessageWrapper(self.create_purchase_more_msg(warehouse_id, product_id, description, count, seqnum))
        cfg.logger.info('Purchase more.')
        self.send(send_wrapper)

    def purchase_more_recv(self, recv_wrapper):      
        # send ack back to world
        cfg.logger.info('Send acks: {}'.format(world_seqnum))
        ack_wrapper = MessageWrapper(self.create_acks_msg_in_batch(recv_wrapper.get_data().arrived))
        ack_wrapper.encode_and_send(self.socket)
        return recv_wrapper

    def call_truck_send(self, package_id, warehouse_id, product_ids, descriptions, counts, owner, dest_x, dest_y, seqnum):
        send_wrapper = MessageWrapper(self.create_truck_call_msg(
            package_id, warehouse_id, product_ids, descriptions, counts, owner, dest_x, dest_y, seqnum))
        cfg.logger.info('Call a truck from the UPS.')
        recv_wrapper = self.send_ups(send_wrapper)

    def call_truck_recv(self, recv_wrapper, packages_data): # truck arrived
        num_of_arrived_truck = len(recv_wrapper.get_data().truckArrived)
        for i in range(num_of_arrived_truck):
            for key, package in packages_data.items():
                truck_id = get_truckid_from_sql(key)
                if truck_id is None:
                    truck_id = recv_wrapper.get_data().truckArrived[i].truck_id
                    assert truck_id is not None
                    db_command = 'UPDATE miniamazon_app_ordercollection SET truck_id = ' + str(truck_id) + \
                    ' WHERE order_collection_id = ' + str(key)
                    db_interface = DBInterface(cfg.db_name, cfg.db_user, cfg.db_password, cfg.db_host, cfg.db_port)
                    db_interface.setup_excecute_and_close(db_command)
                    break


        # for key, package in packages_data.items():
        #     truck_id = get_truckid_from_sql(key)
        #     if truck_id is None:
        #         truck_id = recv_wrapper.get_data().truckArrived[0].truck_id
        #         assert truck_id is not None
        #         db_command = 'UPDATE miniamazon_app_ordercollection SET truck_id = ' + str(truck_id) + \
        #         ' WHERE order_collection_id = ' + str(key)
        #         db_interface = DBInterface(cfg.db_name, cfg.db_user, cfg.db_password, cfg.db_host, cfg.db_port)
        #         db_interface.setup_excecute_and_close(db_command)
        #         break

        return recv_wrapper

    def packing_send(self, warehouse_id, product_ids, descriptions, counts, shipid, seqnum):
        send_wrapper = MessageWrapper(self.create_pack_msg(warehouse_id, product_ids, descriptions, counts, shipid, seqnum))
        cfg.logger.info('Sending packing message to the warehouse.')
        self.send(send_wrapper)
    
    def packing_recv(self, recv_wrapper, packages_data):
        # send ack back to world
        ack_wrapper = MessageWrapper(self.create_acks_msg_in_batch(recv_wrapper.get_data().ready))
        cfg.logger.info('Send acks: {}'.format(ack_wrapper.parse_itself(wapb.ACommands)))
        ack_wrapper.encode_and_send(self.socket)
        for data in recv_wrapper.get_data().ready:
            key = data.shipid
            db_command = 'UPDATE miniamazon_app_ordercollection SET status = \'Packed\'' + \
                ' WHERE order_collection_id = ' + str(key)
            db_interface = DBInterface(cfg.db_name, cfg.db_user, cfg.db_password, cfg.db_host, cfg.db_port)
            db_interface.setup_excecute_and_close(db_command)
        return recv_wrapper

    def put_on_truck_send(self, warehouse_id, truckid, shipid, seqnum):
        send_wrapper = MessageWrapper(self.create_put_on_truck_msg(warehouse_id, truckid, shipid, seqnum))
        cfg.logger.info('Sending put on truck message to the warehouse.')
        self.send(send_wrapper)

    def put_on_truck_recv(self, recv_wrapper, packages_data):
        # send ack back to world
        ack_wrapper = MessageWrapper(self.create_acks_msg_in_batch(recv_wrapper.get_data().loaded))
        cfg.logger.info('Send acks: {}'.format(ack_wrapper.parse_itself(wapb.ACommands)))
        ack_wrapper.encode_and_send(self.socket)
        for data in recv_wrapper.get_data().loaded:
            key = data.shipid
            db_command = 'UPDATE miniamazon_app_ordercollection SET status = \'Loaded\'' + \
                ' WHERE order_collection_id = ' + str(key)
            db_interface = DBInterface(cfg.db_name, cfg.db_user, cfg.db_password, cfg.db_host, cfg.db_port)
            db_interface.setup_excecute_and_close(db_command)
        return recv_wrapper

    def go_deliver_send(self, truckid, package_id, dest_x, dest_y, seqnum):
        send_wrapper = MessageWrapper(self.create_go_deliver_msg(truckid, package_id, dest_x, dest_y, seqnum))
        cfg.logger.info('Go deliver.')
        recv_wrapper = self.send_ups(send_wrapper)

    def go_deliver_recv(self, recv_wrapper, packages_data):
        for data in recv_wrapper.get_data().delivered:
            key = data.packageid
            db_command = 'UPDATE miniamazon_app_ordercollection SET status = \'Delivered\'' + \
                ' WHERE order_collection_id = ' + str(key)
            db_interface = DBInterface(cfg.db_name, cfg.db_user, cfg.db_password, cfg.db_host, cfg.db_port)
            db_interface.setup_excecute_and_close(db_command)
        return recv_wrapper