// SPDX-License-Identifier: MIT
pragma solidity ^0.6.0;
//https://github.com/daifoundation/maker-otc/blob/master/src/matching_market.sol
import "./Account.sol";

contract Engine {
    struct Offer
    {
        uint amount;
        address user;
    }
    struct Orders
    {
        uint price_next;
        uint price_prev;
        mapping (uint => Offer) offers;
        uint genesis_offer;
        uint offers_quantity;
    }
    struct OrderBook
    {
        mapping (uint => Orders) offers_buy;
        uint price_buy_max;
        uint price_buy_min;
        uint count_buy;
        mapping (uint => Orders) offers_sell;
        uint price_sell_min;
        uint price_sell_max;
        uint count_sell;
    }

    mapping (address => OrderBook) Books;
    Account user_wallet;
    constructor (address wallet) public {user_wallet = Account(wallet);}
    function buyOffer(address user, address token, uint price, uint amount) public
    {
        uint sum_price = price * amount;
        require(user_wallet.eth_balanceOf(user) >= sum_price);
        OrderBook storage order_token = Books[token];
        if (price < order_token.price_sell_min || order_token.count_sell == 0)
            storeBuyOrder(user, token, price, amount);
        else
        {
            uint ethAmount = 0;
            uint remain = amount;
            uint buyPrice = order_token.price_sell_min;
            uint counter;
            while (buyPrice <= price && remain > 0)
            {
                counter = order_token.offers_sell[buyPrice].genesis_offer;
                while (counter <= order_token.offers_sell[buyPrice].offers_quantity && remain > 0)
                {
                    uint currAmount = order_token.offers_sell[buyPrice].offers[counter].amount;
                    ethAmount = currAmount * buyPrice;
                    user_wallet.send_eth(user, order_token.offers_sell[buyPrice].offers[counter].user, ethAmount);
                    user_wallet.send_token(order_token.offers_sell[buyPrice].offers[counter].user, user, token, currAmount);
                    order_token.offers_sell[buyPrice].offers[counter].amount = 0;
                    order_token.offers_sell[buyPrice].genesis_offer = order_token.offers_sell[buyPrice].genesis_offer + 1;
                    remain = remain - currAmount;
                }
                buyPrice = order_token.price_sell_min;
            }
            if (remain > 0) buyOffer(user, token, price, remain);
        }
    }
    function storeBuyOrder (address user, address token, uint price, uint amount) public
    {
        OrderBook storage order_token = Books[token];
        order_token.offers_buy[price].offers_quantity = order_token.offers_buy[price].offers_quantity + 1;
        order_token.offers_buy[price].offers[order_token.offers_buy[price].offers_quantity] = Offer(amount, user);
        if (order_token.offers_buy[price].offers_quantity == 1)
        {
            order_token.offers_buy[price].genesis_offer = 1;
            order_token.count_buy = order_token.count_buy + 1;
            uint price_current = order_token.price_buy_max;
            uint price_min = order_token.price_buy_min;


            if (price_min >= price || price_min == 0)
            {
                if (price_current == 0 )
                {
                    order_token.price_buy_max = price;
                    order_token.offers_buy[price].price_next = price;
                    order_token.offers_buy[price].price_prev = 0;
                }
                else
                {
                    order_token.offers_buy[price_min].price_prev = price;
                    order_token.offers_buy[price].price_next = price_min;
                    order_token.offers_buy[price].price_prev = 0;
                }
                order_token.price_buy_min = price;
            }
        }
    }
    function sellOffer(address user, address token, uint price, uint amount) public
    {
        require(user_wallet.token_balanceOf(user, token) >= amount);
        OrderBook storage order_token = Books[token];
        if (order_token.count_buy == 0 || price < order_token.price_buy_max)
            storeSellOrder(user, token, price, amount);
        else
        {
            uint ethAmount = 0;
            uint remain = amount;
            uint sellPrice = order_token.price_sell_min;
            uint counter;
            while (sellPrice >= price && remain > 0) { //order execution loop
                counter = order_token.offers_buy[sellPrice].genesis_offer;
                while (counter <= order_token.offers_buy[sellPrice].offers_quantity && remain > 0)
                {
                    uint currAmount = order_token.offers_buy[sellPrice].offers[counter].amount;
                    if (currAmount <= remain)
                    {
                        ethAmount = currAmount * sellPrice;
                        user_wallet.send_eth(order_token.offers_buy[sellPrice].offers[counter].user, user, ethAmount);
                        user_wallet.send_token(user, order_token.offers_buy[sellPrice].offers[counter].user, token, currAmount);
                        order_token.offers_buy[sellPrice].offers[counter].amount = 0;
                        order_token.offers_buy[sellPrice].genesis_offer = order_token.offers_buy[sellPrice].genesis_offer + 1;
                        remain = remain - currAmount;
                    }
                    counter = counter + 1;
                }
                sellPrice = order_token.price_buy_max;
            }
            if (remain > 0) sellOffer(user, token, price, remain);
        }
    }
    function storeSellOrder (address user, address token, uint price, uint amount) public
    {
        OrderBook storage order_token = Books[token];
        order_token.offers_sell[price].offers_quantity = order_token.offers_sell[price].offers_quantity + 1;
        order_token.offers_sell[price].offers[order_token.offers_sell[price].offers_quantity] = Offer(amount, user);
        if (order_token.offers_sell[price].offers_quantity == 1)
        {
                order_token.offers_sell[price].genesis_offer = 1;
                order_token.count_sell = order_token.count_sell + 1;
                uint price_current = order_token.price_sell_min;
                uint maxPrice = order_token.price_sell_max;
                if (price_current == 0 )
                {
                    order_token.price_sell_min = price;
                    order_token.offers_sell[price].price_next = price;
                    order_token.offers_sell[price].price_prev = 0;
                } else
                {
                    order_token.offers_sell[maxPrice].price_next = price;
                    order_token.offers_sell[price].price_prev = maxPrice;
                    order_token.offers_sell[price].price_next = price;
                }
                order_token.price_sell_max = price;
        }
    }
    function getBuyOrders (address token) public view returns (uint[] memory, uint[] memory)
    {
        OrderBook storage order_token = Books[token];
        uint[] memory prices = new uint[](order_token.count_buy);
        uint[] memory amounts = new uint[](order_token.count_buy);
        uint buyPrice = order_token.price_buy_min;
        uint q = 0;
        if (order_token.price_buy_max > 0)
        {
            while (buyPrice <= order_token.price_buy_max)
            {
                prices[q] = buyPrice;
                uint priceAmount = 0;
                uint counter = order_token.offers_buy[buyPrice].genesis_offer;
                while (counter <= order_token.offers_buy[buyPrice].offers_quantity)
                {
                    priceAmount = priceAmount + order_token.offers_buy[buyPrice].offers[counter].amount;
                    counter = counter + 1;
                }
                amounts[q] = priceAmount;
                if (buyPrice == order_token.offers_buy[buyPrice].price_next) break;
                else buyPrice = order_token.offers_buy[buyPrice].price_next;
                q = q + 1;
            }
        }
        return(prices, amounts);
    }

    function getSellOrders (address token) public view returns (uint[] memory, uint[] memory)
    {
        OrderBook storage order_token = Books[token];
        uint[] memory prices = new uint[](order_token.count_sell);
        uint[] memory amounts = new uint[](order_token.count_sell);
        uint sellPrice = order_token.price_sell_min;
        uint q = 0;
        if (order_token.price_sell_min > 0)
        {
            while (sellPrice <= order_token.price_sell_max)
            {
                prices[q] = sellPrice;
                uint priceAmount = 0;
                uint counter = order_token.offers_sell[sellPrice].genesis_offer;
                while (counter <= order_token.offers_sell[sellPrice].offers_quantity)
                {
                    priceAmount = priceAmount + order_token.offers_sell[sellPrice].offers[counter].amount;
                    counter = counter + 1;
                }
                if (sellPrice == order_token.offers_sell[sellPrice].price_next) break;
                else sellPrice = order_token.offers_sell[sellPrice].price_next;
                q = q + 1;
            }
        }
        return(prices, amounts);
    }
    function removeOrder (address user, address token, bool sell_order, uint price) public
    {
        OrderBook storage order_token = Books[token];
        uint q = order_token.offers_sell[price].genesis_offer;
        while (q <= order_token.offers_sell[price].offers_quantity)
        {
            if (order_token.offers_sell[price].offers[q].user == user)
                order_token.offers_sell[price].offers[q].amount = 0;
            q = q + 1;
        }
    }
}