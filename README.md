# Odoo POS Session Auto Closer

This script allows you to automatically close Point of Sale (POS) sessions in Odoo that are in a 'closing control' state. It validates all orders in the session and then closes it.

## Requirements
- Python 3
- Odoo installation with XML-RPC enabled

## Usage
To use the script, simply run it with Python 3 and pass in the IDs of the POS sessions you want to close as arguments. For example:

```
python3 close_session.py -pos=11,13
```

This will close all POS sessions with IDs 11 and 13.

## Setup
Before running the script, you will need to set up the following environment variables:
- ODOO_URL: the URL of your Odoo instance
- ODOO_DB: the name of your Odoo database
- ODOO_USERNAME: the username for your Odoo account
- ODOO_PASSWORD: the password for your Odoo account

You can set these variables in your .bash_profile file.

The script also logs all activity to a file named 'closing.log' in the same directory as the script.

## Contributing
Feel free to submit a pull request or open an issue if you have any suggestions or find any bugs.

## License
This script is licensed under the MIT License.
