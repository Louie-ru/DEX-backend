// SPDX-License-Identifier: MIT
pragma solidity ^0.6.0;
// based on https://github.com/bokkypoobah/Tokens/blob/master/contracts/FixedSupplyToken.sol
// https://stackoverflow.com/questions/67409550/implementing-buying-and-selling-in-solidity
contract Token
{
    address public baseAddress;
    string public symbol;
    address public owner_;
    string public name;
    uint8 public decimals;
    event Approval(address indexed tokenOwner, address indexed spender, uint tokens);
    event Transfer(address indexed from, address indexed to, uint tokens);
    mapping(address => uint256) public balances;
    mapping(address => mapping (address => uint256)) allowed;
    uint256 totalSupply_;
    constructor(uint256 total, string memory _name, string memory _symbol, uint8 _decimals, address _owner) public
    {
    	totalSupply_ = total;
    	balances[_owner] = totalSupply_;
    	name =  _name;
    	symbol = _symbol;
    	decimals=_decimals;
    	owner_ = _owner;
    	baseAddress = address(this);
    }
    function approve(address delegate, uint numTokens) public returns (bool)
    {
        allowed[msg.sender][delegate] = numTokens;
        emit Approval(msg.sender, delegate, numTokens);
        return true;
    }
    function transfer(address ownerIn, address receiver, uint numTokens) public returns (bool)
    {
        require(numTokens <= balances[ownerIn]);
        balances[ownerIn] = balances[ownerIn] - numTokens;
        balances[receiver] = balances[receiver] + numTokens;
        emit Transfer(ownerIn, receiver, numTokens);
        return true;
    }
    function allowance(address owner, address delegate) public view returns (uint)
    {
        return allowed[owner][delegate];
    }
    function totalSupply() public view returns (uint256)
    {
	    return totalSupply_;
    }
    function transferFrom(address owner, address buyer, uint numTokens) public returns (bool)
    {
        require(numTokens <= balances[owner]);
        balances[owner] = balances[owner] - numTokens;
        allowed[owner][msg.sender] = allowed[owner][msg.sender] - numTokens;
        balances[buyer] = balances[buyer] + numTokens;
        emit Transfer(owner, buyer, numTokens);
        return true;
    }
    function balanceOf(address tokenOwner) public view returns (uint)
    {
        return balances[tokenOwner];
    }

}
