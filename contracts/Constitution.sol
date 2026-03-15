// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract Constitution {
    string public constant RULES = "Only ethical, non-harmful services; no gambling, no illegal content; sustainable compute usage simulation.";

    function getConstitution() external pure returns (string memory) {
        return RULES;
    }
}
