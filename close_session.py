import xmlrpc.client
import datetime
import time
import logging
import os

# Storing credentials in .bash_profile
url = os.environ['ODOO_URL']
db = os.environ['ODOO_DB']
username = os.environ['ODOO_USERNAME']
password = os.environ['ODOO_PASSWORD']

print(f"Connecting to {url} to databse {db} with credentials from {username}")

# Log in and get the user ID 
common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})

# Create the models proxy
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

# Find all opened POS sessions for POS Stores with specific IDs
# Replace IDs with your specific POS configuration IDs
opened_sessions = models.execute_kw(db, uid, password, 'pos.session', 'search', [[
    ('state', '=', 'closing_control'),
    ('config_id', 'in', [13,8])
]])

# Set up Logging: 
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('closing.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


print('Configuration and Connection OK')
print(f"Sessions in Closing Control: {str(len(opened_sessions))}")
logger.info(f"Odoo Session Auto Closer: Configuration and Connection OK")
logger.info(f"Sessions in Closing Control: {str(len(opened_sessions))}")

# Close all sessions in state CLOSING CONTROL
for session_id in opened_sessions:
    print(f"Identified open session {session_id}")
    try:
        print(f"Try closing session {session_id}")
        logger.info(f"Try closing session {session_id}")
        session = models.execute_kw(db, uid, password, 'pos.session', 'read', [session_id], {'fields': ['state', 'cash_register_difference']})[0]
        
        print(f"Session {session_id} cash difference: {session['cash_register_difference']}")
        logger.info(f"Session {session_id} cash difference: {session['cash_register_difference']}")
        start_time = time.time()
        # Defining 1500 COP as max difference
        if session['cash_register_difference'] >= -1500 and session['cash_register_difference'] <= 1500:
            print('Validating all orders of the session')
            logger.info(f"Validating all orders of session {session_id}")
            
            # Validating all orders
            can_close = models.execute_kw(db, uid, password, 'pos.session', 'action_pos_session_validate', [session_id])
            if can_close: # is true in case all orders were validated
                # Get the open session information
                session_data = models.execute_kw(db, uid, password, 'pos.session', 'read', [[session_id]], {'fields': ['config_id', 'stop_at']})[0]
                pos_name = session_data['config_id'][1]
                pos_id = session_data['config_id'][0]

                print('All orders validated successfully. Now closing the session')
                logger.info(f"POS ID {pos_id}: All orders validated successfully. Now closing session {session_id}")
                # Close the session and record the duration
                
                models.execute_kw(db, uid, password, 'pos.session', 'action_pos_session_close', [session_id])
                print(f"Session {session_id} closed successfully.")
                logger.info(f"POS ID {pos_id}: Session {session_id} closed successfully.")
                end_time = time.time()
                duration = int(end_time - start_time)

                # Time Formatting:
                dt_object_start = datetime.datetime.fromtimestamp(start_time)
                formatted_time_start = dt_object_start.strftime('%d-%m-%Y %H:%M:%S')
                dt_object_end = datetime.datetime.fromtimestamp(end_time)
                formatted_time_end = dt_object_start.strftime('%d-%m-%Y %H:%M:%S')

                print(f"POS ID {pos_id}: Session closing took {duration} seconds")
                logger.info(f"POS ID {pos_id}: Session closing took {duration} seconds")
            else:
                print(f"Error: Orders of session {session_id} could not be validated")
                logger.info(f"Error: Orders of session {session_id} could not be validated for some reasons")

        else:
            # Log the session that could not be closed
            session_data = models.execute_kw(db, uid, password, 'pos.session', 'read', [[session_id]], {'fields': ['config_id']})[0]
            pos_name = session_data['config_id'][1]
            pos_id = session_data['config_id'][0]
            end_time = time.time()
            duration = int(end_time - start_time)

            # Time Formatting:
            dt_object_start = datetime.datetime.fromtimestamp(start_time)
            formatted_time_start = dt_object_start.strftime('%d-%m-%Y %H:%M:%S')
            dt_object_end = datetime.datetime.fromtimestamp(end_time)
            formatted_time_end = dt_object_start.strftime('%d-%m-%Y %H:%M:%S')

            logger.info(f"Session {session_id} cannot be closed due to high theoretical closing balance of {session['cash_register_difference']} COP")
            print(f"Session {session_id} cannot be closed due to high theoretical closing balance of {session['cash_register_difference']} COP")

    except Exception as e:
        print(f"Error closing session {session_id}: {e}")
        logger.info(f"Error closing session {session_id}: {e}")
        