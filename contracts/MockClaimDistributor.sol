// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Local/demo only — stand-in for a merkle or points "claim" target.
contract MockClaimDistributor {
    event Claimed(address indexed user, uint256 amount);

    mapping(address => uint256) public claimed;

    function claim(uint256 amount) external {
        require(amount > 0 && amount <= 1 ether, "amount");
        claimed[msg.sender] += amount;
        emit Claimed(msg.sender, amount);
    }
}
