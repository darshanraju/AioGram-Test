import requests
import json
# We import our db module, as it will be convenient to add from here
# transactions to the database
import db

# This is the beginning of our requests
MAINNET_API_BASE = "https://toncenter.com/api/v2/"
TESTNET_API_BASE = "https://testnet.toncenter.com/api/v2/"

# Find out which network we are working on
with open('config.json', 'r') as f:
    config_json = json.load(f)
    MAINNET_API_TOKEN = config_json['MAINNET_API_TOKEN']
    TESTNET_API_TOKEN = config_json['TESTNET_API_TOKEN']
    MAINNET_WALLET = config_json['MAINNET_WALLET']
    TESTNET_WALLET = config_json['TESTNET_WALLET']
    WORK_MODE = config_json['WORK_MODE']

if WORK_MODE == "mainnet":
    API_BASE = MAINNET_API_BASE
    API_TOKEN = MAINNET_API_TOKEN
    WALLET = MAINNET_WALLET
else:
    API_BASE = TESTNET_API_BASE
    API_TOKEN = TESTNET_API_TOKEN
    WALLET = TESTNET_WALLET

def detect_address(address):
    url = f"{API_BASE}detectAddress?address={address}&api_key={API_TOKEN}"
    r = requests.get(url)
    response = json.loads(r.text)
    try:
        return response['result']['bounceable']['b64url']
    except:
        return False
    
def get_address_transactions():
    url = f"{API_BASE}getTransactions?address={WALLET}&limit=30&archival=true&api_key={API_TOKEN}"
    r = requests.get(url)
    response = json.loads(r.text)
    return response['result']

def find_transaction(user_wallet, value, comment):
        # Get the last 30 transactions
    transactions = get_address_transactions()
    for transaction in transactions:
                # Select the incoming "message" - transaction
        msg = transaction['in_msg']
        if msg['source'] == user_wallet and msg['value'] == value and msg['message'] == comment:
                        # If all the data match, we check that this transaction
                        # we have not verified before
            t = db.check_transaction(msg['body_hash'])
            if t == False:
                                # If not, we write in the table to the verified
                                # and return True
                db.add_v_transaction(
                    msg['source'], msg['body_hash'], msg['value'], msg['message'])
                print("find transaction")
                print(
                    f"transaction from: {msg['source']} \nValue: {msg['value']} \nComment: {msg['message']}")
                return True
                        # If this transaction is already verified, we check the rest, we can find the right one
            else:
                pass
        # If the last 30 transactions do not contain the required one, return False
        # Here you can add code to see the next 29 transactions
        # However, within the scope of the Example, this would be redundant.
    return False

