// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "forge-std/Test.sol";
import "../AgentRevenueService.sol";

contract AgentRevenueServiceTest is Test {
    AgentRevenueService public service;
    address public treasury;
    address public financeDistributor;
    address public user;

    function setUp() public {
        treasury = makeAddr("treasury");
        financeDistributor = makeAddr("financeDistributor");
        user = makeAddr("user");
        service = new AgentRevenueService(treasury, financeDistributor);
        vm.deal(user, 1 ether);
    }

    function test_fulfillQuery_minPayment() public {
        vm.prank(user);
        service.fulfillQuery{value: 0.001 ether}("test-metadata");
        vm.expectRevert(AgentRevenueService.InsufficientPayment.selector);
        vm.prank(user);
        service.fulfillQuery{value: 0.0009 ether}("x");
    }

    function test_fulfillQuery_splitsFees() public {
        vm.prank(user);
        service.fulfillQuery{value: 0.001 ether}("meta");
        assertEq(treasury.balance, 0.0001 ether);
        assertEq(financeDistributor.balance, 0.0005 ether);
    }

    function test_pause_unpause() public {
        service.pause();
        vm.expectRevert();
        vm.prank(user);
        service.fulfillQuery{value: 0.001 ether}("x");
        service.unpause();
        vm.prank(user);
        service.fulfillQuery{value: 0.001 ether}("x");
        assertEq(financeDistributor.balance, 0.0005 ether);
    }
}
