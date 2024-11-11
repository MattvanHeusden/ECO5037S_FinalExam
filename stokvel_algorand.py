import random
import algosdk
from algosdk import mnemonic
from algosdk import transaction
from algosdk.transaction import PaymentTxn
from algosdk.v2client import algod
import time

# Connect to Algorand testnet
algod_token = "stkvl"
algod_address = "https://testnet-api.algonode.cloud"
client = algod.AlgodClient(algod_token, algod_address)

# # Function to create account and return address & private key
# def create_account():
#     private_key, address = account.generate_account()
#     passphrase = mnemonic.from_private_key(private_key)
#     print("Account Address:", address)
#     print("Account Mnemonic:", passphrase)
#     return private_key, address

# # prefunded account details
# funding_private_key = "corn utility idle alpha wish ecology law crawl parrot trouble cream stone coach edit reunion alpha trigger sister salon artist tape card advice ability timber"
# funding_address = "S6HCF7U4SMZEBJZGP2JLTP62NCIXNRF5XU6OAIEL3V2R5UAY7IGIFX42GA"

# # create accounts and fund them from prefunded account
# accounts = []
# for i in range(5):
#     print(f"Creating and funding Account {i + 1}")
#     private_key, address = create_account()
#     accounts.append({"address": address, "private_key": private_key})

#     # Fund the account with 25 Algos (5 Algos per monht for 5 months)
#     params = client.suggested_params()
#     txn = PaymentTxn(funding_address, params, address, 25_000_000) 
#     signed_txn = txn.sign(funding_private_key)
#     client.send_transaction(signed_txn)
#     print(f"Funded account {address} with 25 Algos.")

# List of existing accounts (with private keys)
existing_accounts = [
    {"address": "VCYNJKZXZQ7ABELJN35JGHMBZ3WXPNEVJPKUJO4UVC65C52EWOTU32NSGA", "private_key": mnemonic.to_private_key("brain erosion oval lonely amount observe maximum arrive verb jump voice fitness pig goat pencil pave slot under property hover coach smart talk absorb scissors"), "paid": False, "opted_out": False},
    {"address": "U2LJPPMU45H6OBRXPVBE36DBV65UDCBT37Z5XEVFHIM5NMUL6RJOQOWZIU", "private_key": mnemonic.to_private_key("syrup wealth chapter inspire churn envelope whip field heavy cost nerve scout mixed wire shallow achieve tunnel balcony cool cluster skin pumpkin creek absent yard"), "paid": False, "opted_out": False},
    {"address": "TSDTYIC3MX4OSX5SHEILY66ONSR7OZPD66SSUJNLC3TJN2TJSSNXYJ7CYM", "private_key": mnemonic.to_private_key("fashion process wave chaos prepare moment club evidence acid symptom detail security pill control occur fame seat casual express dose burden grain reason abstract dirt"), "paid": False, "opted_out": False},
    {"address": "44RC7TDGGRHTVKCKYNOMLIWYQYVNTX4EUD7L5ROWZVBSEUKJ7TBX4VHMK4", "private_key": mnemonic.to_private_key("salt retire light pioneer slab okay flip zoo always uniform shift found club deputy repeat garage glow mixture basket final whisper castle monkey absent taste"), "paid": False, "opted_out": False},
    {"address": "ZUN7RBLZE6OCK3LNPUOWUEIPXQTMDCNNC2Y7TMAC7YM3XHFAQRO2N43J2A", "private_key": mnemonic.to_private_key("deliver canvas raccoon hour remember unveil refuse gun profit physical dirt spray anxiety mass churn brown parent coast give essence veteran run share about fiscal"), "paid": False, "opted_out": False}
]

# Create multisig account with 4/5 quorum
version = 1
threshold = 4  
# create a multisig transactoin
msig = transaction.Multisig(
    version,
    threshold,
    ["VCYNJKZXZQ7ABELJN35JGHMBZ3WXPNEVJPKUJO4UVC65C52EWOTU32NSGA", 
     "U2LJPPMU45H6OBRXPVBE36DBV65UDCBT37Z5XEVFHIM5NMUL6RJOQOWZIU", 
     "TSDTYIC3MX4OSX5SHEILY66ONSR7OZPD66SSUJNLC3TJN2TJSSNXYJ7CYM",
     "44RC7TDGGRHTVKCKYNOMLIWYQYVNTX4EUD7L5ROWZVBSEUKJ7TBX4VHMK4",
     "ZUN7RBLZE6OCK3LNPUOWUEIPXQTMDCNNC2Y7TMAC7YM3XHFAQRO2N43J2A"
     ],
)
# get multisig address
multisig_address = msig.address()
print("Multisig Address: ", msig.address())

# function for deposit into the multisig account
def deposit_to_stokvel():
    for account in existing_accounts:
        if not account["opted_out"]:
            params = client.suggested_params()
            txn = PaymentTxn(account["address"], params, multisig_address, 5_000_000) 
            signed_txn = txn.sign(account["private_key"])
            client.send_transaction(signed_txn)
            print(f"Deposited 5 Algos from {account["address"]} to multisig account.")

# function to choose member and make payout
def payout():
    eligible_members = [account["address"] for account in existing_accounts if not account["paid"] and not account["opted_out"]]
    if not eligible_members:
        print("All members have been paid or opted out. Ending the stokvel cycle.")
        return False  # stop cycle if no one is eligible for payout

    recipient = random.choice(eligible_members)
    params = client.suggested_params()

    # make a PaymentTxn fro multisig account
    msig_pay = transaction.PaymentTxn(
        msig.address(),
        params,
        recipient,
        15_000_000,
        close_remainder_to=recipient
    )

    # Create the multisig transaction
    msig_txn = transaction.MultisigTransaction(msig_pay, msig)
   
    for account in existing_accounts:
        #get private key and sign transaction
        private_key = account["private_key"]
        msig_txn.sign(private_key)

    # Send  multisig transaction
    try:
        txid = client.send_transaction(msig_txn)
        result = transaction.wait_for_confirmation(client, txid, 4)  # Wait for confirmation
        print(f"Payout of 15 Algos sent to {recipient}. Confirmed in round {result['confirmed-round']}.")
        
        # mark the receiver as paid
        for account in existing_accounts:
            if account["address"] == recipient:
                account["paid"] = True
    except Exception as e:
        print(f"Error sending payout: {e}")

    return True

# function to handle opt-out after 5 months.
def handle_opt_out():
    for account in existing_accounts:
        if account["paid"]:  # check to see if member has been paid
            opt_out = input(f"End of Stokvel cycle. Member {account['address']} has been paid. Do they want to opt out (y/n)? ")
            if opt_out.lower() == 'y':
                account["opted_out"] = True
                print(f"Member {account['address']} opted out.")


def stokvel_cycle():
    while True:  # Indefinite loop for continuous stokvel cycles
        for i in range(1, 6):
            print(f"--- Starting a new Stokvel Cycle ---")
            # Deposit to stokvel
            deposit_to_stokvel()
            
            # make payout
            if not payout():
                print("No eligible members for payout, continuing to next cycle.")
            
            time.sleep(2) 

        # opt-out option after 5 months
        handle_opt_out()

        # Check if any member opted out to stop cycle
        if any(account["opted_out"] for account in existing_accounts):
            print("A member has opted out. Ending stokvel cycle.")
            break 

# Run stokvel cycle
stokvel_cycle()



