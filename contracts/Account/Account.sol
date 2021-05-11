// SPDX-License-Identifier: MIT
pragma solidity ^0.6.0;

import "./Token.sol";

contract Account{
    event deposit_ethereum (address indexed account, uint256 amount);
    event withdraw_ethereum (address indexed account, uint256 amount);
    event create_token (address indexed account, address indexed token, string name);
    struct userWallet
    {
        mapping(address => uint256) balances;
        uint256 ethereum_balance;
    }
    mapping (address => userWallet) public wallets;
    address tokenAddr;
    constructor() public {}
    function sub_token_balance (address owner, address token, uint amount) public
    {
        require (wallets[owner].balances[token] >= amount);
        wallets[owner].balances[token] = wallets[owner].balances[token] - amount;
    }
    function deposit_ethereum_ (address user) public payable
    {
        wallets[user].ethereum_balance = wallets[user].ethereum_balance + msg.value;
        deposit_ethereum(user, msg.value);
    }
    function createToken (address user, uint256 total, string memory name, string memory symbol, uint8 decimals) public
    {
        Token c = new Token(total, name, symbol, decimals, user);
        wallets[user].balances[address(c)] = total;
        create_token(user, c.baseAddress(), name);
        tokenAddr = c.baseAddress();
    }
    function create_wallet (address user) public
    {
        wallets[user] = userWallet(0);
    }
    function add_ethereum (address user, uint amount) public
    {
        wallets[user].ethereum_balance = wallets[user].ethereum_balance + amount;
    }
    function token_get_balance(address owner, address token) public view returns (uint)
    {
        return wallets[owner].balances[token];
    }
    function add_token (address user, address token_addr) public
    {
        Token c = Token(token_addr);
        wallets[user].balances[token_addr] = c.balances(user);
    }
    function send_ethereum (address user, address receiver, uint256 amount) public
    {

        wallets[user].ethereum_balance = wallets[user].ethereum_balance - amount;
        wallets[receiver].ethereum_balance = wallets[receiver].ethereum_balance + amount;
    }
    function sub_ethereum (address user, uint amount) public
    {
        require (wallets[user].ethereum_balance >= amount);
        wallets[user].ethereum_balance = wallets[user].ethereum_balance - amount;
    }
    function withdraw (address payable user, uint256 amount) public
    {
        require (amount <= wallets[user].ethereum_balance, "Not enough balance");
        wallets[user].ethereum_balance = wallets[user].ethereum_balance - amount;
        user.transfer(amount);
        withdraw_ethereum(user, amount);
    }
    function add_token_balance (address owner, address token, uint amount) public
    {
        wallets[owner].balances[token] = wallets[owner].balances[token] + amount;
    }
    function get_symbol (address token) public view returns(string memory)
    {
        Token c = Token(token);
        return c.symbol();
    }
    function getAddr () public view returns(address)
    {
        return tokenAddr;
    }
    function ethereum_get_balance (address owner) public view returns (uint)
    {
        return wallets[owner].ethereum_balance;
    }
}
