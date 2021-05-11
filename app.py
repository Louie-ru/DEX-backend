from flask import Flask, request
from web3 import HTTPProvider, Web3
import json
from flask import jsonify
from flask_cors import CORS, cross_origin

app = Flask(__name__)
CORS(app, support_credentials=True)


def web3_get_account(account_addr):
    return get_web3().eth.account.privateKeyToAccount(priv_key(account_addr))


def name_by_account(w3_account):
    accounts = user_accounts()
    for acc in accounts.items():
        if acc[1]["address"] == w3_account.address:
            return acc[0]
    return None


def priv_key(account_addr):
    accounts = user_accounts()
    for acc in accounts.items():
        if acc[1]["address"] == account_addr:
            return acc[1]["key"]
    return None


def user_accounts():
    with open('config.json') as accounts_file:
        return json.load(accounts_file)


def get_web3():
    return Web3(Web3.HTTPProvider("http://localhost:8545"))


def contract_info(contract_name):
    global contract_addresses
    with open(f"contracts/{contract_name}/{contract_name}.abi") as abi_file:
        abi = json.loads(abi_file.read())
    return contract_addresses[contract_name], abi


def user_balances(w3_account):
    eth_balance = dict()
    eth_balance['ticker'] = "ETH"
    eth_balance['balance'] = int(get_web3().eth.getBalance(w3_account.address)) / 1000000000000000000
    return [eth_balance]


def deploy(name_contract):
    w3 = Web3(HTTPProvider("http://127.0.0.1:8545"))
    global wallet_addr
    global contract_addresses
    with open(f"contracts/{name_contract}/{name_contract}.abi") as abi_file:
        abi = json.loads(abi_file.read())
    with open(f"contracts/{name_contract}/{name_contract}.bin") as bin_file:
        bytecode = json.loads(bin_file.read())
    p_key = next(iter(user_accounts().values()))["key"]
    w3.eth.account = w3.eth.account.privateKeyToAccount(p_key)
    current_contract = w3.eth.contract(abi=abi, bytecode=bytecode["object"])
    transact_id = None
    if name_contract == "Token":
        transact_id = current_contract.constructor(1000, "Token", "TKN", 10, w3.eth.account.address).transact({'from': w3.eth.account.address})
    elif name_contract == "Account":
        transact_id = current_contract.constructor().transact({'from': w3.eth.account.address})
    elif name_contract == "Engine":
        transact_id = current_contract.constructor(wallet_addr).transact({'from': w3.eth.account.address})
    transact_receipt = w3.eth.waitForTransactionReceipt(transact_id)
    if transact_receipt['status']:
        print(f"Contract {name_contract} deployed successfully at address: " + transact_receipt['contractAddress'])
    contract_addresses[name_contract] = transact_receipt['contractAddress']
    if name_contract == "Account":
        wallet_addr = transact_receipt['contractAddress']


contract_addresses = {}
tokens_db = {}
wallet_addr = ''
deploy('Token')
deploy('Account')
deploy('Engine')


@app.route('/<account_address>/account/profile_coins', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def coins_profile(account_address):
    w3 = get_web3()
    w3_account = web3_get_account(account_address)
    w3.eth.defaultAccount = w3_account
    address, abi = contract_info("Account")
    contract = w3.eth.contract(address=address, abi=abi)
    name = name_by_account(w3_account)
    message = 'Success'
    try:
        contract.functions.eth_balanceOf(w3_account.address).call({'from': w3_account.address}) / 1000000000000000000
    except Exception as e:
        message = e
    response = dict()
    response['address'] = account_address
    response['alias'] = name
    response['message'] = message
    return jsonify(response)


@app.route('/<account_address>/account/profile_coins/create_token', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def create_token(account_address):
    global tokens_db
    w3 = get_web3()
    w3_account = web3_get_account(account_address)
    w3.eth.defaultAccount = w3_account
    address, abi = contract_info("Account")
    name = name_by_account(w3_account)
    contract = w3.eth.contract(address=address, abi=abi)
    if request.method == "POST":
        total_supply = request.json['tot']
        name = request.json['name']
        symbol = request.json['sym']
        decimals = request.json['dec']
        hash_transaction = contract.functions.createToken(w3_account.address, int(total_supply), name, symbol, int(decimals)).transact({'from': w3_account.address})
        w3.eth.waitForTransactionReceipt(hash_transaction)
        token_addr = contract.functions.getAddr().call({'from': w3_account.address})
        tokens_db[symbol] = token_addr
    response = dict()
    response['address'] = account_address
    response['alias'] = name
    return jsonify(response)


@app.route('/<account_address>/account/eth_management/send_eth', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def send_ethereum(account_address):
    w3 = get_web3()
    w3_account = web3_get_account(account_address)
    w3.eth.defaultAccount = w3_account
    address, abi = contract_info("Account")
    name = name_by_account(w3_account)
    contract = w3.eth.contract(address=address, abi=abi)
    message = ''
    if request.method == "POST":
        receiver = request.json['rec']
        amount = request.json['amo']
        try:
            hash_transaction = contract.functions.send_eth(w3_account.address, receiver, int(float(amount) * 1000000000000000000)).transact({'from': w3_account.address})
            w3.eth.waitForTransactionReceipt(hash_transaction)
        except Exception as e:
            message = e
    response = dict()
    response['address'] = account_address
    response['alias'] = name
    response['message'] = message
    return jsonify(response)


@app.route('/<account_address>/account/profile_coins/available_coins', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def coins_available(account_address):
    global tokens_db
    w3 = get_web3()
    w3_account = web3_get_account(account_address)
    w3.eth.defaultAccount = w3_account
    address, abi = contract_info("Account")
    contract = w3.eth.contract(address=address, abi=abi)
    name = name_by_account(w3_account)
    tickers = list()
    balances = []
    for sym, tok_address in tokens_db.items():
        token_balance = contract.functions.token_balanceOf(w3_account.address, tok_address).call({'from': w3_account.address})
        balances.append(token_balance)
        coin = dict()
        coin['ticker'] = sym
        coin['address'] = tok_address
        coin['balance'] = token_balance
        tickers.append(coin)
    response = dict()
    response['address'] = account_address
    response['tickers'] = tickers
    response['alias'] = name
    return jsonify(response)


@app.route('/<account_address>/account/profile_coins/view_dom/<token>', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_dom(account_address, token):
    global tokens_db
    w3 = get_web3()
    w3_account = web3_get_account(account_address)
    w3.eth.defaultAccount = w3_account
    address, abi = contract_info("Engine")
    contract = w3.eth.contract(address=address, abi=abi)
    message = ''
    token_addr = tokens_db[token]
    buy_ord = contract.functions.getBuyOrders(token_addr).call({'from': w3_account.address})
    sell_ord = contract.functions.getSellOrders(token_addr).call({'from': w3_account.address})
    name = name_by_account(w3_account)
    response = dict()
    response['address'] = account_address
    response['message'] = message
    response['token'] = token
    response['alias'] = name
    response['buyOrders'] = buy_ord
    response['sellOrders'] = sell_ord
    return jsonify(response)


@app.route('/<account_address>/account/profile_coins/remove_order/<token>', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def remove_order(account_address, token):
    w3 = get_web3()
    w3_account = web3_get_account(account_address)
    w3.eth.defaultAccount = w3_account
    address, abi = contract_info("Engine")
    contract = w3.eth.contract(address=address, abi=abi)
    message = ''
    if request.method == 'POST':
        global tokens_db
        token_addr = tokens_db[token]
        sell_order = request.json['sell']
        sell_order = True if sell_order == "sell" else False
        price = request.json['pri']
        hash_transaction = contract.functions.removeOrder(w3_account.address, token_addr, sell_order, int(price) * 1000000000000000000).transact({'from': w3_account.address})
        w3.eth.waitForTransactionReceipt(hash_transaction)
    name = name_by_account(w3_account)
    response = dict()
    response['address'] = account_address
    response['message'] = message
    response['token'] = token
    response['alias'] = name
    return jsonify(response)


@app.route('/<account_address>/account/profile_coins/send_token', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def token_snd(account_address):
    global tokens_db
    w3 = get_web3()
    w3_account = web3_get_account(account_address)
    w3.eth.defaultAccount = w3_account
    address, abi = contract_info("Account")
    contract = w3.eth.contract(address=address, abi=abi)
    message = ''
    if request.method == "POST":
        receiver = request.json['rec']
        amount = request.json['amo']
        token_addr = tokens_db[request.json['tic']]
        hash_transaction = contract.functions.send_token(w3_account.address, receiver, token_addr, int(amount)).transact({'from': w3_account.address})
        w3.eth.waitForTransactionReceipt(hash_transaction)
    name = name_by_account(w3_account)
    response = dict()
    response['address'] = account_address
    response['message'] = message
    response['alias'] = name
    return jsonify(response)


@app.route('/<account_address>/account/profile_coins/sell_token/<token>', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def token_sell(account_address, token):
    global tokens_db
    w3 = get_web3()
    w3_account = web3_get_account(account_address)
    w3.eth.defaultAccount = w3_account
    address, abi = contract_info("Engine")
    contract = w3.eth.contract(address=address, abi=abi)
    message = ''
    if request.method == "POST":
        price = request.json['pri']
        amount = request.json['amo']
        token_addr = tokens_db[token]
        hash_transaction = contract.functions.sellOffer(w3_account.address, token_addr, int(float(price) * 1000000000000000000), int(amount)).transact({'from': w3_account.address})
        w3.eth.waitForTransactionReceipt(hash_transaction)
    name = name_by_account(w3_account)
    response = dict()
    response['address'] = account_address
    response['message'] = message
    response['alias'] = name
    response['token'] = token
    return jsonify(response)


@app.route('/<account_address>/account/profile_coins/buy_token/<token>', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def wallet_buy_token(account_address, token):
    global tokens_db
    w3 = get_web3()
    w3_account = web3_get_account(account_address)
    w3.eth.defaultAccount = w3_account
    address, abi = contract_info("Engine")
    contract = w3.eth.contract(address=address, abi=abi)
    message = ''
    if request.method == "POST":
        price = request.json['pri']
        amount = request.json['amo']
        token_addr = tokens_db[token]
        hash_transaction = contract.functions.buyOffer(w3_account.address, token_addr, int(float(price) * 1000000000000000000), int(amount)).transact({'from': w3_account.address})
        w3.eth.waitForTransactionReceipt(hash_transaction)
    name = name_by_account(w3_account)
    response = dict()
    response['address'] = account_address
    response['message'] = message
    response['alias'] = name
    response['token'] = token
    return jsonify(response)


@app.route('/check_pass', methods=['POST'])
@cross_origin(supports_credentials=True)
def check_pass():
    address = request.json['address']
    password = request.json['key']
    found = False
    db = user_accounts()
    for user in db:
        if db[user]["address"] == address and db[user]["key"] == password:
            found = True
    response = dict()
    response['status'] = found
    return jsonify(response)


@app.route('/<account_address>')
@cross_origin(supports_credentials=True)
def get_specific_account(account_address):
    w3_account = web3_get_account(account_address)
    name = name_by_account(w3_account)
    balances = user_balances(w3_account)
    response = dict()
    response['address'] = w3_account.address
    response['balances'] = balances
    response['alias'] = name
    return jsonify(response)


@app.route('/<account_address>/account')
@cross_origin(supports_credentials=True)
def account_wall(account_address):
    w3_account = web3_get_account(account_address)
    name = name_by_account(w3_account)
    response = dict()
    response['alias'] = name
    response['address'] = w3_account.address
    return response


@app.route('/<account_address>/account/create_wallet')
@cross_origin(supports_credentials=True)
def new_wallet(account_address):
    w3 = get_web3()
    w3_account = web3_get_account(account_address)
    name = name_by_account(w3_account)
    w3.eth.defaultAccount = w3_account
    address, abi = contract_info("Account")
    contract = w3.eth.contract(address=address, abi=abi)
    hash_transaction = contract.functions.create_wallet(w3_account.address).transact({'from': w3_account.address})
    tx_receipt = w3.eth.waitForTransactionReceipt(hash_transaction)
    if tx_receipt['status']:
        message = 'Wallet is created!'
    else:
        message = "Fail"
    response = dict()
    response['address'] = account_address
    response['alias'] = name
    response['message'] = message
    return jsonify(response)


@app.route('/<account_address>/account/eth_management', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def wallet_profile(account_address):
    w3 = get_web3()
    w3_account = web3_get_account(account_address)
    w3.eth.defaultAccount = w3_account
    address, abi = contract_info("Account")
    name = name_by_account(w3_account)
    contract = w3.eth.contract(address=address, abi=abi)
    try:
        eth_balance = contract.functions.eth_balanceOf(w3_account.address).call({'from': w3_account.address}) / 1000000000000000000
        message = ''
        if request.method == "POST":
            if request.json['dep'] != '':
                eth = request.json['dep']
            elif request.json['with'] != '':
                eth = request.json['with']
            else:
                eth = 0
            value = w3.toWei(float(eth), 'ether')
            if request.json['dep'] != '':
                hash_transaction = contract.functions.deposit_eth(w3_account.address).transact({'from': w3_account.address, 'value': value})
                w3.eth.waitForTransactionReceipt(hash_transaction)
            elif request.json['with'] != '':
                try:
                    hash_transaction = contract.functions.withdraw(w3_account.address, value).transact({'from': w3_account.address})
                    w3.eth.waitForTransactionReceipt(hash_transaction)
                except Exception as e:
                    message = e
    except Exception as e:
        eth_balance = 0
        message = e
    response = dict()
    response['balance'] = eth_balance
    response['address'] = account_address
    response['alias'] = name
    response['message'] = message
    return jsonify(response)


@app.route('/')
@cross_origin(supports_credentials=True)
def get_accounts():
    accounts = user_accounts()
    addresses = [acc[1]["address"] for acc in accounts.items()]
    names = [acc[0] for acc in accounts.items()]
    users = list()
    for i in range(0, len(names)):
        user = dict()
        user['id'] = i
        user['alias'] = names[i]
        user['address'] = addresses[i]
        users.append(user)
    return jsonify(users)
