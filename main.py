from web3 import Web3
from web3.middleware import geth_poa_middleware
from loguru import logger
from config import ABI_ZETA, ABI_SWAP, RPC


class Swaper:
    def __init__(self, provider: str, privatekey: str):
        self.provider = provider
        self.w3 = Web3(Web3.HTTPProvider(provider))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.token = self.w3.to_checksum_address('0x000080383847bD75F91c168269Aa74004877592f')
        self.bsc_swap = self.w3.to_checksum_address('0xa0b5Cbdc4D14c4f4D36483EC0dE310919F3B2d90')
        self.polygon_swap = self.w3.to_checksum_address('0xaf28cb0d9e045170e1642321b964740784e7dc64')
        self.privatekey = privatekey
        self.address = None

    def get_balance(self) -> bool:
        try:
            self.address = self.w3.eth.account.from_key(self.privatekey).address
            contract = self.w3.eth.contract(self.token, abi=ABI_ZETA)

            if self.w3.from_wei(contract.functions.balanceOf(self.address).call(), 'ether') < 3:
                logger.error(f'Not enough coins. Minimum of 3: {self.address}, chainID: {self.w3.eth.chain_id}')
                return False
            if self.w3.eth.get_balance(self.address) == 0:
                logger.error(f'0 native coins on balance: {self.address}, chainID: {self.w3.eth.chain_id}')
                return False
            else:
                return True
        except Exception as e:
            logger.error(f'Error get balance: {self.address} {e}, chainID: {self.w3.eth.chain_id}')
            return False

    def approve(self) -> bool:
        try:
            contract = self.w3.eth.contract(self.token, abi=ABI_ZETA)
            nonce = self.w3.eth.get_transaction_count(self.address)

            if 'binance' in self.provider:
                approve = self.bsc_swap
            else:
                approve = self.polygon_swap

            tx = contract.functions.approve(
                approve,
                3 * 10**18).build_transaction(
                {
                    'chainId': self.w3.eth.chain_id,
                    'from': self.address,
                    'nonce': nonce,
                    'gasPrice': self.w3.eth.gas_price,
                    'gas': 100_000
                }
            )

            signed_tx = self.w3.eth.account.sign_transaction(tx, self.privatekey)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt['status'] == 1:
                logger.success(f'Success approve: {self.address}, chainID: {self.w3.eth.chain_id}')
                return True

            logger.error(f'Fail approve: {self.address}, chainID: {self.w3.eth.chain_id}')
            return False

        except Exception as e:
            logger.error(f'Fail approve transaction: {self.address}, chainID: {self.w3.eth.chain_id}\n{e}')
            return False

    def swap(self) -> bool:
        try:
            if 'binance' in self.provider:
                contract_address = self.w3.to_checksum_address(self.bsc_swap)
                to_chain = 80001
            else:
                contract_address = self.w3.to_checksum_address(self.polygon_swap)
                to_chain = 97
            contract = self.w3.eth.contract(contract_address, abi=ABI_SWAP)
            nonce = self.w3.eth.get_transaction_count(self.address)

            tx = contract.functions.swapTokensForTokensCrossChain(
                self.token,
                3 * 10**18,
                self.address,
                self.token,
                False,
                0,
                to_chain,
                350000
            ).build_transaction(
                {
                    'chainId': self.w3.eth.chain_id,
                    'from': self.address,
                    'nonce': nonce,
                    'gasPrice': self.w3.eth.gas_price,
                    'gas': 500_000
                }
            )

            signed_tx = self.w3.eth.account.sign_transaction(tx, self.privatekey)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt['status'] == 1:
                logger.success(f'Success swap: {self.address}, chainID: {self.w3.eth.chain_id}')
                return True

            logger.error(f'Fail swap: {self.address}, chainID: {self.w3.eth.chain_id}')
            return False

        except Exception as e:
            logger.error(f'Fail swap transaction: {self.address}, chainID: {self.w3.eth.chain_id}\n{e}')
            return False


if __name__ == '__main__':
    with open('privatekeys.txt') as file:
        keys = [row.strip() for row in file]

    for key in keys:
        for i in RPC:
            swaper = Swaper(i, key)
            if swaper.get_balance():
                if swaper.approve():
                    if swaper.swap():
                        break
                else:
                    continue
            else:
                continue
