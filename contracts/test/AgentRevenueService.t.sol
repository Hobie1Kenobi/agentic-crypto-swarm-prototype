// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "forge-std/Test.sol";
import "../AgentRevenueService.sol";

contract RevertingReceiver {
    receive() external payable {
        revert("reject");
    }
}

contract AgentRevenueServiceTest is Test {
    AgentRevenueService public service;
    address public treasury;
    address public financeDistributor;
    address public user;
    address public owner;

    function setUp() public {
        treasury = makeAddr("treasury");
        financeDistributor = makeAddr("financeDistributor");
        user = makeAddr("user");
        owner = address(this);
        service = new AgentRevenueService(treasury, financeDistributor);
        vm.deal(user, 10 ether);
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

    function test_fulfillQuery_emitsFeeDistributed() public {
        vm.prank(user);
        vm.expectEmit(true, true, true, true);
        emit AgentRevenueService.FeeDistributed(treasury, 0.0001 ether);
        vm.expectEmit(true, true, true, true);
        emit AgentRevenueService.FeeDistributed(financeDistributor, 0.0005 ether);
        service.fulfillQuery{value: 0.001 ether}("meta");
    }

    function test_fulfillQuery_remainderStaysInContract() public {
        vm.prank(user);
        service.fulfillQuery{value: 1 ether}("meta");
        uint256 protocolFee = 1 ether * 1000 / 10000;
        uint256 distributable = 1 ether * 5000 / 10000;
        assertEq(treasury.balance, protocolFee);
        assertEq(financeDistributor.balance, distributable);
        assertEq(address(service).balance, 1 ether - protocolFee - distributable);
    }

    function test_setTreasury() public {
        address newTreasury = makeAddr("newTreasury");
        service.setTreasury(newTreasury);
        assertEq(service.treasury(), newTreasury);
        vm.prank(user);
        service.fulfillQuery{value: 0.001 ether}("x");
        assertEq(newTreasury.balance, 0.0001 ether);
    }

    function test_setFinanceDistributor() public {
        address newDist = makeAddr("newDist");
        service.setFinanceDistributor(newDist);
        assertEq(service.financeDistributor(), newDist);
        vm.prank(user);
        service.fulfillQuery{value: 0.001 ether}("x");
        assertEq(newDist.balance, 0.0005 ether);
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

    function test_constructor_revertsZeroTreasury() public {
        vm.expectRevert(AgentRevenueService.InvalidAddress.selector);
        new AgentRevenueService(address(0), financeDistributor);
    }

    function test_constructor_revertsZeroFinance() public {
        vm.expectRevert(AgentRevenueService.InvalidAddress.selector);
        new AgentRevenueService(treasury, address(0));
    }

    function test_setTreasury_onlyOwner() public {
        vm.prank(user);
        vm.expectRevert();
        service.setTreasury(makeAddr("newTreasury"));
    }

    function test_setFinanceDistributor_onlyOwner() public {
        vm.prank(user);
        vm.expectRevert();
        service.setFinanceDistributor(makeAddr("newDist"));
    }

    function test_pause_onlyOwner() public {
        vm.prank(user);
        vm.expectRevert();
        service.pause();
    }

    function test_unpause_onlyOwner() public {
        service.pause();
        vm.prank(user);
        vm.expectRevert();
        service.unpause();
    }

    function test_fulfillQuery_exactMinPayment() public {
        vm.prank(user);
        service.fulfillQuery{value: 0.001 ether}("exact");
        assertEq(treasury.balance, 0.0001 ether);
        assertEq(financeDistributor.balance, 0.0005 ether);
        assertEq(address(service).balance, 0.0004 ether);
    }

    function test_fulfillQuery_emitsQueryFulfilled() public {
        vm.prank(user);
        bytes32 expectedHash = keccak256(abi.encodePacked(block.timestamp, user, "m"));
        vm.expectEmit(true, true, true, true);
        emit AgentRevenueService.QueryFulfilled(expectedHash, user, 0.001 ether, "m");
        service.fulfillQuery{value: 0.001 ether}("m");
    }

    function test_fulfillQuery_transferFailedReverts() public {
        RevertingReceiver reverter = new RevertingReceiver();
        service.setTreasury(address(reverter));
        vm.prank(user);
        vm.expectRevert(AgentRevenueService.TransferFailed.selector);
        service.fulfillQuery{value: 0.001 ether}("x");
    }

    function test_receive_acceptsEther() public {
        vm.deal(address(service), 5 ether);
        assertEq(address(service).balance, 5 ether);
        vm.prank(user);
        service.fulfillQuery{value: 0.001 ether}("m");
        assertEq(address(service).balance, 5 ether + 0.0004 ether);
    }

    function test_feeSplitCorrectness_largeValue() public {
        uint256 pay = 100 ether;
        vm.deal(user, pay);
        vm.prank(user);
        service.fulfillQuery{value: pay}("large");
        assertEq(treasury.balance, 10 ether);
        assertEq(financeDistributor.balance, 50 ether);
        assertEq(address(service).balance, 40 ether);
    }
}
