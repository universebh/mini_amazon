import config as cfg
import psycopg2 as pg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


class DBInterface:
    def __init__(self, name, user, password, host, port):
        self.name = name
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.conn = None
        self.cursor = None

    def setup(self):
        try:
            conn = pg2.connect(
                host=self.host, 
                port=self.port, 
                database=self.name, 
                user=self.user, 
                password=self.password
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            self.conn = conn
            self.cursor = cursor
        except (Exception, pg2.DatabaseError) as error:
            cfg.logger.debug(error)

    def close_cursor(self):
        if self.cursor is not None:
            self.cursor.close()
            self.cursor = None

    def close_conn(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def close(self):
        self.close_cursor()
        self.close_conn()

    def execute(self, cmd, verbose=True):
        assert self.conn is not None
        assert self.cursor is not None
        self.cursor.execute(cmd)
        if verbose:
            cfg.logger.info('DB command: {};'.format(cmd))
        # for row in self.cursor.fetchall():
        #     cfg.logger.info('DB command: {}...'.format(row))
        #     break

    def setup_excecute_and_close(self, cmd, verbose=True):
        self.setup()
        self.execute(cmd, verbose)
        self.close()
