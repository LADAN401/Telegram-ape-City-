import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher()

w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))
if not w3.is_connected():
    raise Exception("Cannot connect to Base RPC")

account = w3.eth.account.from_key(os.getenv('PRIVATE_KEY'))

CONTRACT_ADDRESS = Web3.to_checksum_address(os.getenv('CONTRACT_ADDRESS'))
with open('abi.json', 'r') as f:
    ABI = f.read()

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

@dp.message(Command('start'))
async def start(message: types.Message):
    await message.reply(
        "🏙️🐒 *Ape City Launchpad on Base*\n\n"
        "Launch memecoins for FREE (gas only)\n"
        "Bonding curve → Auto Uniswap V3 migration\n"
        "Creator gets 0.1 ETH reward\n\n"
        "Use /launch to start!",
        parse_mode='Markdown'
    )

@dp.message(Command('launch'))
async def launch(message: types.Message):
    await message.reply(
        "Reply with token details:\n\n"
        "`Name|Symbol|Supply`\n\n"
        "Example:\n"
        "`Cool Ape|CAPE|1000000000`",
        parse_mode='Markdown'
    )

@dp.message(F.text)
async def handle_launch(message: types.Message):
    text = message.text.strip()
    if '|' not in text:
        return

    parts = text.split('|', 2)
    if len(parts) != 3:
        return await message.reply("❌ Invalid format. Use: Name|Symbol|Supply")

    name, symbol, supply_str = [p.strip() for p in parts]

    try:
        supply = int(supply_str) * 10**18
    except:
        return await message.reply("❌ Invalid supply number")

    try:
        await message.reply("🚀 Launching your token... (10-40 seconds)")

        nonce = w3.eth.get_transaction_count(account.address)
        tx = contract.functions.launchToken(name, symbol, supply).build_transaction({
            'chainId': 8453,
            'gas': 6000000,
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce,
        })

        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=200)

        # Correctly extract token address from TokenLaunched event
        events = contract.events.TokenLaunched().process_receipt(receipt)
        token_ca = events[0]['args']['token']

        await message.reply(
            f"✅ *Token Launched Successfully!*\n\n"
            f"Name: {name}\n"
            f"Symbol: {symbol}\n"
            f"Supply: {int(supply_str):,}\n\n"
            f"🔗 Token CA: `{token_ca}`\n"
            f"🔗 Tx: https://basescan.org/tx/{tx_hash.hex()}\n\n"
            f"Trading live on bonding curve!\n"
            f"Auto-migrates at 4.2 ETH raised 🏙️🐒",
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    except Exception as e:
        logging.error(f"Error: {e}")
        await message.reply(f"❌ Launch failed:\n`{str(e)[:500]}`", parse_mode='Markdown')

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
