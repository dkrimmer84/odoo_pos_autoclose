import xmlrpc.client
import time
import logging
import os
import argparse
import http.client
from xmlrpc.client import Transport

class TimeoutTransport(Transport):
    def __init__(self, timeout=3600, *args, **kwargs):
        self.timeout = timeout
        super().__init__(*args, **kwargs)

    def make_connection(self, host):
        conn = http.client.HTTPConnection(host, timeout=self.timeout)
        return conn
    
class Autocloser():
    # Storing credentials in .bash_profile
    url = os.environ['ODOO_URL']
    db = os.environ['ODOO_DB']
    username = os.environ['ODOO_USERNAME']
    password = os.environ['ODOO_PASSWORD']
    logging_file = 'closing.log'
    max_cash_register_difference_default = 1500 # positive and negative
    odoo_server_timeout = 3600

    # Set up Logging: 
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(logging_file)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    def __init__(self, point_of_sales, max_cash_register_difference):
        self.point_of_sales = point_of_sales
        self.max_cash_register_difference = self.max_cash_register_difference_default
        if max_cash_register_difference:
            self.max_cash_register_difference = max_cash_register_difference

    def login(self):
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.url))
        uid = common.authenticate(self.db, self.username, self.password, {})
        return uid

    def get_open_sessions(self):
        uid = self.login()
        print(f"Connecting to {self.url} to databse {self.db} with credentials from {self.username}") 
        # Create the models proxy
        # models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.url), timeout=self.odoo_server_timeout)
        timeout_transport = TimeoutTransport(timeout=self.odoo_server_timeout)
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.url), transport=timeout_transport)

        # Find all opened POS sessions for POS Stores with specific IDs
        # Replace IDs with your specific POS configuration IDs
        opened_sessions = models.execute_kw(self.db, uid, self.password, 'pos.session', 'search', [[
            ('state', '=', 'closing_control'),
            ('config_id', 'in', self.point_of_sales)
        ]])

        print('Configuration and Connection OK')
        print(f"Maximum cash register difference allowed: {str(self.max_cash_register_difference)}")
        print(f"Sessions in Closing Control: {str(len(opened_sessions))}")
        self.logger.info(f"Odoo Session Auto Closer: Configuration and Connection OK")
        self.logger.info(f"Maximum cash register difference allowed: {str(self.max_cash_register_difference)}")
        self.logger.info(f"Sessions in Closing Control: {str(len(opened_sessions))}")

        return opened_sessions

    def close_session(self):
        if not self.setup_logging:
            return False
        uid = self.login()
        # Close all sessions in state CLOSING CONTROL
        opened_sessions = self.get_open_sessions()
        for session_id in opened_sessions:
            # models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.url), timeout=self.odoo_server_timeout)
            timeout_transport = TimeoutTransport(timeout=self.odoo_server_timeout)
            models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.url), transport=timeout_transport)
            print(f"Identified open session {session_id}")
            try:
                print(f"Try closing session {session_id}")
                self.logger.info(f"Try closing session {session_id}")
                session = models.execute_kw(self.db, uid, self.password, 'pos.session', 'read', [session_id], {'fields': ['state', 'cash_register_difference']})[0]
                
                print(f"Session {session_id} cash difference: {session['cash_register_difference']}")
                self.logger.info(f"Session {session_id} cash difference: {session['cash_register_difference']}")
                start_time = time.time()
                # Defining 1500 COP as max difference
                if session['cash_register_difference'] >= (self.max_cash_register_difference*-1) and session['cash_register_difference'] <= self.max_cash_register_difference:
                    print('Validating all orders of the session')
                    self.logger.info(f"Validating all orders of session {session_id}")
                    
                    # Validating all orders
                    can_close = models.execute_kw(self.db, uid, self.password, 'pos.session', 'action_pos_session_validate', [session_id])
                    if can_close: # is true in case all orders were validated
                        # Get the open session information
                        session_data = models.execute_kw(self.db, uid, self.password, 'pos.session', 'read', [[session_id]], {'fields': ['config_id', 'stop_at']})[0]
                        # pos_name = session_data['config_id'][1]
                        pos_id = session_data['config_id'][0]

                        print('All orders validated successfully. Now closing the session')
                        self.logger.info(f"POS ID {pos_id}: All orders validated successfully. Now closing session {session_id}")
                        # Close the session and record the duration
                        
                        # Lets close the session after all orders were validated
                        models.execute_kw(self.db, uid, self.password, 'pos.session', 'action_pos_session_close', [session_id])
                        print(f"Session {session_id} closed successfully.")
                        self.logger.info(f"POS ID {pos_id}: Session {session_id} closed successfully.")
                        end_time = time.time()
                        duration = int(end_time - start_time)

                        print(f"POS ID {pos_id}: Session closing took {duration} seconds")
                        self.logger.info(f"POS ID {pos_id}: Session closing took {duration} seconds")
                    else:
                        print(f"Error: Orders of session {session_id} could not be validated")
                        self.logger.info(f"Error: Orders of session {session_id} could not be validated for some reasons")

                else:
                    # Log the session that could not be closed
                    session_data = models.execute_kw(self.db, uid, self.password, 'pos.session', 'read', [[session_id]], {'fields': ['config_id']})[0]
                    pos_id = session_data['config_id'][0]
                    self.logger.info(f"POS ID {pos_id}: cannot be closed due to high theoretical closing balance of {session['cash_register_difference']} COP")
                    print(f"POS ID {pos_id}: cannot be closed due to high theoretical closing balance of {session['cash_register_difference']} COP")

            except Exception as e:
                print(f"Error closing session {session_id}: {e}")
                self.logger.info(f"Error closing session {session_id}: {e}")

    def setup_logging(self):
        if os.path.exists(self.logging_file):
            return True
        else:
            try:
                with open(self.logging_file, "w") as f:
                    f.write("")
                    os.chmod(self.logging_file, 0o777)
                return True
            except Exception as e:
                print(f"Error creating log file: {e}")
                return False
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Autoclose POS sessions in Odoo')
    parser.add_argument('-pos', '--point_of_sales', type=str, help='comma separated list of POS IDs to close', required=True)
    parser.add_argument('-maxdiff', '--max-cash-register-difference', dest='max_cash_register_difference', type=int, help='maximum cash register difference to allow when closing a session')
    args = parser.parse_args()
    point_of_sales = [int(pos_id) for pos_id in args.point_of_sales.split(',')]
    max_cash_register_difference=args.max_cash_register_difference if args.max_cash_register_difference else False
    auto_closer = Autocloser(point_of_sales, max_cash_register_difference)
    auto_closer.close_session()