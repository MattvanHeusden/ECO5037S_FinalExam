from algosdk import transaction, mnemonic
from algosdk.transaction import AssetConfigTxn, AssetTransferTxn, PaymentTxn
from algosdk.v2client import algod

# Connect to Algorand testnet
algod_token = ""
algod_address = "https://testnet-api.algonode.cloud"
algod_client = algod.AlgodClient(algod_token, algod_address)


UCTZAR_INITIAL_AMOUNT = 100000000  # initial amount for UCTZAR stablecoin
ALGO_UCTZAR_RATIO = 0.5  # 1 UCTZAR = 0.5 ALGO
TRANSACTION_FEE_PERCENTAGE = 0.01  # 1% fee

# Liquidity provider and trader account details
lp_private_key = mnemonic.to_private_key("fashion process wave chaos prepare moment club evidence acid symptom detail security pill control occur fame seat casual express dose burden grain reason abstract dirt")
lp_address = "TSDTYIC3MX4OSX5SHEILY66ONSR7OZPD66SSUJNLC3TJN2TJSSNXYJ7CYM"

trading_accounts = [
    {"address": "VCYNJKZXZQ7ABELJN35JGHMBZ3WXPNEVJPKUJO4UVC65C52EWOTU32NSGA", "private_key": mnemonic.to_private_key("brain erosion oval lonely amount observe maximum arrive verb jump voice fitness pig goat pencil pave slot under property hover coach smart talk absorb scissors")},
    {"address": "U2LJPPMU45H6OBRXPVBE36DBV65UDCBT37Z5XEVFHIM5NMUL6RJOQOWZIU", "private_key": mnemonic.to_private_key("syrup wealth chapter inspire churn envelope whip field heavy cost nerve scout mixed wire shallow achieve tunnel balcony cool cluster skin pumpkin creek absent yard")}
]

# Create UCTZAR stablecoin
def create_uctzar_asset(creator_private_key, creator_address):
    params = algod_client.suggested_params()
    txn = AssetConfigTxn(
        sender=creator_address,
        sp=params,
        total=UCTZAR_INITIAL_AMOUNT,
        default_frozen=False,
        unit_name="UCTZAR",
        asset_name="SouthAfricanRandStablecoin",
        manager=creator_address,
        reserve=creator_address,
        freeze=creator_address,
        clawback=creator_address,
        decimals=2
    )
    signed_txn = txn.sign(creator_private_key)
    tx_id = algod_client.send_transaction(signed_txn)
    wait_for_confirmation(tx_id)
    response = algod_client.pending_transaction_info(tx_id)
    asset_id = response["asset-index"]
    print(f"Created UCTZAR asset with ID: {asset_id}")
    return asset_id

# Wait for confirmation
def wait_for_confirmation(tx_id):
    last_round = algod_client.status().get("last-round")
    while True:
        tx_info = algod_client.pending_transaction_info(tx_id)
        if "confirmed-round" in tx_info and tx_info["confirmed-round"] > 0:
            print(f"Transaction {tx_id} confirmed in round {tx_info['confirmed-round']}.")
            break
        else:
            print("Waiting for confirmation...")
            algod_client.status_after_block(last_round + 1)

# opt in for asset (need to for trading accounts to receive UCTZAR)
def opt_in_asset(account_address, account_private_key, asset_id):
    params = algod_client.suggested_params()
    opt_in_txn = AssetTransferTxn(account_address, params, account_address, 0, asset_id)
    signed_txn = opt_in_txn.sign(account_private_key)
    tx_id = algod_client.send_transaction(signed_txn)
    wait_for_confirmation(tx_id)
    print(f"{account_address} has opted into asset {asset_id}")

# function to provide liquidity 
def provide_liquidity(lp_address, lp_private_key, algo_amount, uctzar_amount, uctzar_asset_id):
    params = algod_client.suggested_params()
    algo_txn = PaymentTxn(lp_address, params, lp_address, algo_amount)
    uctzar_txn = AssetTransferTxn(lp_address, params, lp_address, uctzar_amount, uctzar_asset_id)

    transaction.assign_group_id([algo_txn, uctzar_txn])
    signed_algo_txn = algo_txn.sign(lp_private_key)
    signed_uctzar_txn = uctzar_txn.sign(lp_private_key)

    tx_id = algod_client.send_transactions([signed_algo_txn, signed_uctzar_txn])
    wait_for_confirmation(tx_id)
    print(f"Provided {algo_amount} ALGO and {uctzar_amount} UCTZAR to the liquidity pool.")

# Function to get the account balance for a specific asset
def get_asset_balance(account_address, asset_id):
    account_info = algod_client.account_info(account_address)
    for asset in account_info['assets']:
        if asset['asset-id'] == asset_id:
            return asset['amount']
    return 0

# Function to trade UCTZAR for ALGO
def trade_uctzar_for_algo(sender_address, sender_private_key, uctzar_amount, uctzar_asset_id, algo_amount, fee_percentage=0.01):
    try:
        # check that sender has enough UCTZAR balance
        uctzar_balance = get_asset_balance(sender_address, uctzar_asset_id)
        if uctzar_balance < uctzar_amount:
            print(f"Not enough UCTZAR to trade. Available balance: {uctzar_balance}")
            return

        # fee amount
        fee_amount = int(algo_amount * fee_percentage * 10000)

        # transaction for trading UCTZAR for ALGO
        suggested_params = algod_client.suggested_params()

        # UCTZAR transfer from the sender to the liquidity pool
        transfer_txn = AssetTransferTxn(
            sender=sender_address,
            receiver=lp_address,  
            amt=uctzar_amount,
            index=uctzar_asset_id,
            sp=suggested_params
        )

        # ALGO payment to the sender from the liquidity pool
        payment_txn = PaymentTxn(
            sender=lp_address, 
            receiver=sender_address,
            amt=algo_amount * 10000,
            sp=suggested_params
        )

        # Fee payment to the liquidity provider
        fee_txn = PaymentTxn(
            sender=sender_address,
            receiver=lp_address,
            amt=fee_amount,  
            sp=suggested_params
        )

        # assign group ID for atomic transactions 
        transaction.assign_group_id([transfer_txn, payment_txn, fee_txn])

        # sign transactions
        signed_transfer_txn = transfer_txn.sign(sender_private_key)
        signed_payment_txn = payment_txn.sign(lp_private_key)
        signed_fee_txn = fee_txn.sign(sender_private_key)

        signed_group = [signed_transfer_txn, signed_payment_txn, signed_fee_txn]

        # send tx's
        tx_ids = algod_client.send_transactions(signed_group)

        wait_for_confirmation(tx_ids)

        print(f"Traded {uctzar_amount} UCTZAR for {algo_amount} ALGO with a {fee_amount / 10000} ALGO fee to LP.")
        return tx_ids

    except Exception as e:
        print(f"Error during trade: {e}")
        return None


# function to trade ALGO for UCTZAR
def trade_algo_for_uctzar(trader_address, trader_private_key, algo_amount, uctzar_asset_id, fee_percentage=0.01):
    try:
        # fee amount
        fee_amount = int(algo_amount * fee_percentage * 10000)

        # transaction for swapping ALGO for UCTZAR
        suggested_params = algod_client.suggested_params()

        # ALGO payment from the trader to the liquidity pprovider
        algo_txn = PaymentTxn(
            sender=trader_address,
            receiver=lp_address,
            amt=algo_amount * 10000,
            sp=suggested_params
        )

        # UCTZAR transfer to trader
        uctzar_amount = int(algo_amount / ALGO_UCTZAR_RATIO)
        uctzar_txn = AssetTransferTxn(
            sender=lp_address,
            receiver=trader_address,
            amt=uctzar_amount,
            index=uctzar_asset_id,
            sp=suggested_params
        )

        # Fee payment
        fee_txn = PaymentTxn(
            sender=trader_address,
            receiver=lp_address,
            amt=fee_amount,
            sp=suggested_params
        )

        # assign group ID for atomic transactions
        transaction.assign_group_id([algo_txn, uctzar_txn, fee_txn])

        # sign transactions
        signed_algo_txn = algo_txn.sign(trader_private_key)
        signed_uctzar_txn = uctzar_txn.sign(lp_private_key)
        signed_fee_txn = fee_txn.sign(trader_private_key)

        signed_group = [signed_algo_txn, signed_uctzar_txn, signed_fee_txn]

        # send transactions
        tx_ids = algod_client.send_transactions(signed_group)

        wait_for_confirmation(tx_ids)

        print(f"Traded {algo_amount} ALGO for {uctzar_amount} UCTZAR with {fee_amount / 10000} ALGO transaction fee to LP.")
        return tx_ids

    except Exception as e:
        print(f"Error during trade: {e}")
        return None

# LP withdraws liquidity
def withdraw_liquidity(lp_address, lp_private_key, algo_amount, uctzar_amount, uctzar_asset_id):
    params = algod_client.suggested_params()
    algo_txn = PaymentTxn(lp_address, params, lp_address, algo_amount * 10000)
    uctzar_txn = AssetTransferTxn(lp_address, params, lp_address, uctzar_amount, uctzar_asset_id)

    transaction.assign_group_id([algo_txn, uctzar_txn])
    signed_algo_txn = algo_txn.sign(lp_private_key)
    signed_uctzar_txn = uctzar_txn.sign(lp_private_key)

    tx_id = algod_client.send_transactions([signed_algo_txn, signed_uctzar_txn])
    wait_for_confirmation(tx_id)
    print(f"Withdrew {algo_amount} ALGO and {uctzar_amount} UCTZAR from the liquidity pool.")

# Put together the simulation
def simulation():
    # Create UCTZAR asset
    uctzar_asset_id = create_uctzar_asset(lp_private_key, lp_address)

    # LP opts into the UCTZAR asset
    opt_in_asset(lp_address, lp_private_key, uctzar_asset_id)

    # accounts opts into the UCTZAR asset
    for account in trading_accounts:
        opt_in_asset(account["address"], account["private_key"], uctzar_asset_id)

    # Provide liquidity
    provide_liquidity(lp_address, lp_private_key, 20000000, 10000000, uctzar_asset_id)

    # trade ALGO for UCTZAR with account 1
    trade_algo_for_uctzar(trading_accounts[0]["address"], trading_accounts[0]["private_key"], 500, uctzar_asset_id)

    # Trade UCTZAR for ALGO with account 1
    trade_uctzar_for_algo(trading_accounts[0]["address"], trading_accounts[0]["private_key"], 500, uctzar_asset_id, 250)

    # trade ALGO for UCTZAR with account 2
    trade_algo_for_uctzar(trading_accounts[1]["address"], trading_accounts[1]["private_key"], 200, uctzar_asset_id)

    # Trade UCTZAR for ALGO with account 2
    trade_uctzar_for_algo(trading_accounts[1]["address"], trading_accounts[1]["private_key"], 200, uctzar_asset_id, 100)

    # Withdraw liquidity
    withdraw_liquidity(lp_address, lp_private_key, 500, 500, uctzar_asset_id)

# run simulation
simulation()

