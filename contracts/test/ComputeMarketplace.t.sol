// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "forge-std/Test.sol";
import "../ComputeMarketplace.sol";

contract ComputeMarketplaceTest is Test {
    ComputeMarketplace public marketplace;
    address public miner1;
    address public worker1;
    address public requester1;
    address public validator1;
    address public treasury;
    address public financeDistributor;

    function setUp() public {
        treasury = makeAddr("treasury");
        financeDistributor = makeAddr("financeDistributor");
        marketplace = new ComputeMarketplace(treasury, financeDistributor);
        miner1 = makeAddr("miner1");
        worker1 = makeAddr("worker1");
        requester1 = makeAddr("requester1");
        validator1 = makeAddr("validator1");
        vm.deal(requester1, 10 ether);
        vm.deal(address(marketplace), 1 ether);
    }

    function test_registerMiner() public {
        vm.prank(miner1);
        marketplace.registerAsMiner("agent-1");
        (, string memory m, bool reg) = marketplace.miners(miner1);
        assertTrue(reg);
        assertEq(m, "agent-1");
        assertEq(marketplace.minerCount(), 1);
    }

    function test_registerValidator() public {
        marketplace.setValidatorAllowlist(validator1, true);
        assertTrue(marketplace.validators(validator1));
    }

    function test_submitScoresAndDistribute() public {
        vm.prank(miner1);
        marketplace.registerAsMiner("m1");
        marketplace.setValidatorAllowlist(validator1, true);
        address[] memory addrs = new address[](1);
        addrs[0] = miner1;
        uint256[] memory scores = new uint256[](1);
        scores[0] = 100;
        vm.prank(validator1);
        marketplace.submitScores(addrs, scores);
        vm.prank(validator1);
        marketplace.distributeRewards();
        assertEq(miner1.balance, 1 ether);
        assertEq(address(marketplace).balance, 0);
    }

    function test_submitScores_revertsNotValidator() public {
        vm.prank(miner1);
        marketplace.registerAsMiner("m1");
        address[] memory addrs = new address[](1);
        addrs[0] = miner1;
        uint256[] memory scores = new uint256[](1);
        scores[0] = 100;
        vm.prank(miner1);
        vm.expectRevert(ComputeMarketplace.NotValidator.selector);
        marketplace.submitScores(addrs, scores);
    }

    function test_submitScores_revertsMinerNotRegistered() public {
        marketplace.setValidatorAllowlist(validator1, true);
        address[] memory addrs = new address[](1);
        addrs[0] = miner1;
        uint256[] memory scores = new uint256[](1);
        scores[0] = 100;
        vm.prank(validator1);
        vm.expectRevert(ComputeMarketplace.MinerNotRegistered.selector);
        marketplace.submitScores(addrs, scores);
    }

    function test_submitScores_revertsLengthMismatch() public {
        vm.prank(miner1);
        marketplace.registerAsMiner("m1");
        marketplace.setValidatorAllowlist(validator1, true);
        address[] memory addrs = new address[](1);
        addrs[0] = miner1;
        uint256[] memory scores = new uint256[](2);
        scores[0] = 100;
        scores[1] = 200;
        vm.prank(validator1);
        vm.expectRevert(ComputeMarketplace.InvalidInput.selector);
        marketplace.submitScores(addrs, scores);
    }

    function test_submitScores_revertsEmptyArray() public {
        marketplace.setValidatorAllowlist(validator1, true);
        address[] memory addrs;
        uint256[] memory scores;
        vm.prank(validator1);
        vm.expectRevert(ComputeMarketplace.InvalidInput.selector);
        marketplace.submitScores(addrs, scores);
    }

    function test_registerAsMiner_revertsDuplicate() public {
        vm.prank(miner1);
        marketplace.registerAsMiner("first");
        vm.prank(miner1);
        vm.expectRevert(ComputeMarketplace.InvalidInput.selector);
        marketplace.registerAsMiner("second");
    }

    function test_registerAsMiner_revertsMetadataTooLong() public {
        string memory longMeta;
        for (uint256 i = 0; i < 257; i++) {
            longMeta = string(abi.encodePacked(longMeta, "x"));
        }
        vm.prank(miner1);
        vm.expectRevert(ComputeMarketplace.InvalidInput.selector);
        marketplace.registerAsMiner(longMeta);
    }

    function test_distributeRewards_revertsNoScores() public {
        vm.prank(validator1);
        vm.expectRevert(ComputeMarketplace.NoScores.selector);
        marketplace.distributeRewards();
    }

    function test_distributeRewards_zeroBalanceNoRevert() public {
        ComputeMarketplace empty = new ComputeMarketplace(treasury, financeDistributor);
        vm.prank(miner1);
        empty.registerAsMiner("m1");
        empty.setValidatorAllowlist(validator1, true);
        address[] memory addrs = new address[](1);
        addrs[0] = miner1;
        uint256[] memory scores = new uint256[](1);
        scores[0] = 1;
        vm.prank(validator1);
        empty.submitScores(addrs, scores);
        vm.prank(validator1);
        empty.distributeRewards();
        assertEq(miner1.balance, 0);
    }

    function test_resetRoundScores_onlyOwner() public {
        vm.prank(validator1);
        vm.expectRevert();
        marketplace.resetRoundScores();
    }

    function test_distributeRewards_proportionalSplit() public {
        address miner2 = makeAddr("miner2");
        vm.prank(miner1);
        marketplace.registerAsMiner("m1");
        vm.prank(miner2);
        marketplace.registerAsMiner("m2");
        marketplace.setValidatorAllowlist(validator1, true);
        address[] memory addrs = new address[](2);
        addrs[0] = miner1;
        addrs[1] = miner2;
        uint256[] memory scores = new uint256[](2);
        scores[0] = 300;
        scores[1] = 700;
        vm.prank(validator1);
        marketplace.submitScores(addrs, scores);
        vm.prank(validator1);
        marketplace.distributeRewards();
        assertEq(miner1.balance, 0.3 ether);
        assertEq(miner2.balance, 0.7 ether);
        assertEq(address(marketplace).balance, 0);
    }

    function test_getMiners() public {
        vm.prank(miner1);
        marketplace.registerAsMiner("meta1");
        vm.prank(validator1);
        marketplace.registerAsMiner("meta2");
        (address[] memory addrs, string[] memory metadatas) = marketplace.getMiners();
        assertEq(addrs.length, 2);
        assertEq(metadatas.length, 2);
        assertEq(addrs[0], miner1);
        assertEq(metadatas[0], "meta1");
        assertEq(addrs[1], validator1);
        assertEq(metadatas[1], "meta2");
    }

    function test_taskMarketplace_happyPath_finalizeAndWithdraw() public {
        vm.prank(worker1);
        marketplace.registerAsMiner("worker1-metadata");
        marketplace.setValidatorAllowlist(validator1, true);

        uint256 escrowWei = 1 ether;
        uint256 deadlineAt = block.timestamp + 1 days;

        vm.prank(requester1);
        uint256 taskId = marketplace.createTask{value: escrowWei}(
            "task-metadata",
            "query-what-is-ethical-ai",
            worker1,
            1,
            50,
            deadlineAt
        );

        vm.prank(worker1);
        marketplace.acceptTask(taskId);

        vm.prank(worker1);
        marketplace.submitResult(taskId, "result-metadata-uri");

        vm.prank(validator1);
        marketplace.submitTaskScore(taskId, 80, keccak256("notes"));

        uint256 requesterBalBefore = requester1.balance;
        uint256 workerBalBefore = worker1.balance;
        uint256 treasuryBalBefore = treasury.balance;
        uint256 financeBalBefore = financeDistributor.balance;

        vm.prank(requester1);
        marketplace.finalizeTask(taskId);

        uint256 protocolFeeWei = (escrowWei * marketplace.PROTOCOL_FEE_BPS()) / 10000;
        uint256 financeFeeWei = (escrowWei * marketplace.FINANCE_FEE_BPS()) / 10000;
        uint256 workerPoolWei = escrowWei - protocolFeeWei - financeFeeWei;
        uint256 expectedWorkerPayoutWei = (workerPoolWei * 80) / 100;
        uint256 expectedRefundWei = workerPoolWei - expectedWorkerPayoutWei;

        // Claim pending amounts.
        vm.prank(treasury);
        marketplace.withdraw();
        vm.prank(financeDistributor);
        marketplace.withdraw();
        vm.prank(worker1);
        marketplace.withdraw();
        vm.prank(requester1);
        marketplace.withdraw();

        assertEq(treasury.balance, treasuryBalBefore + protocolFeeWei);
        assertEq(financeDistributor.balance, financeBalBefore + financeFeeWei);
        assertEq(worker1.balance, workerBalBefore + expectedWorkerPayoutWei);
        assertEq(requester1.balance, requesterBalBefore + expectedRefundWei);
        // setUp funds the contract for legacy distributeRewards tests.
        assertEq(address(marketplace).balance, 1 ether);
    }

    function test_taskMarketplace_doubleScoreSubmitReverts() public {
        vm.prank(worker1);
        marketplace.registerAsMiner("worker1-metadata");
        marketplace.setValidatorAllowlist(validator1, true);

        uint256 escrowWei = 0.5 ether;
        uint256 deadlineAt = block.timestamp + 1 days;

        vm.prank(requester1);
        uint256 taskId = marketplace.createTask{value: escrowWei}(
            "task-metadata",
            "query",
            worker1,
            1,
            0,
            deadlineAt
        );

        vm.prank(worker1);
        marketplace.acceptTask(taskId);
        vm.prank(worker1);
        marketplace.submitResult(taskId, "result");

        vm.prank(validator1);
        marketplace.submitTaskScore(taskId, 10, keccak256("n"));
        vm.prank(validator1);
        vm.expectRevert(ComputeMarketplace.AlreadySubmitted.selector);
        marketplace.submitTaskScore(taskId, 11, keccak256("n2"));
    }

    function test_taskMarketplace_cancelRefundsRequester() public {
        vm.prank(worker1);
        marketplace.registerAsMiner("worker1-metadata");

        uint256 escrowWei = 0.25 ether;
        uint256 deadlineAt = block.timestamp + 1 days;

        vm.prank(requester1);
        uint256 taskId = marketplace.createTask{value: escrowWei}(
            "task-metadata",
            "query",
            worker1,
            1,
            0,
            deadlineAt
        );

        uint256 requesterBalBefore = requester1.balance;

        vm.prank(requester1);
        marketplace.cancelTask(taskId);

        vm.prank(requester1);
        marketplace.withdraw();

        assertEq(requester1.balance, requesterBalBefore + escrowWei);
        // setUp funds the contract for legacy distributeRewards tests.
        assertEq(address(marketplace).balance, 1 ether);
    }

    function test_taskMarketplace_finalizeByValidatorAllowed() public {
        vm.prank(worker1);
        marketplace.registerAsMiner("worker1-metadata");
        marketplace.setValidatorAllowlist(validator1, true);

        uint256 escrowWei = 0.4 ether;
        uint256 deadlineAt = block.timestamp + 1 days;

        vm.prank(requester1);
        uint256 taskId = marketplace.createTask{value: escrowWei}(
            "task-metadata",
            "query",
            worker1,
            1,
            0,
            deadlineAt
        );

        vm.prank(worker1);
        marketplace.acceptTask(taskId);
        vm.prank(worker1);
        marketplace.submitResult(taskId, "result");
        vm.prank(validator1);
        marketplace.submitTaskScore(taskId, 50, keccak256("notes"));

        vm.prank(validator1);
        marketplace.finalizeTask(taskId);

        (
            address _requester,
            address _assignedWorker,
            uint256 _escrowWei,
            string memory _taskMetadata,
            string memory _query,
            bytes32 _taskMetadataHash,
            ComputeMarketplace.TaskStatus status,
            uint256 _createdAt,
            uint256 _acceptedAt,
            uint256 _submittedAt,
            uint256 _deadlineAt,
            uint256 _minValidators,
            uint256 _minAverageScore,
            uint256 _scoreSum,
            uint256 _submittedValidators,
            bytes32 _resultHash,
            string memory _resultMetadata
        ) = marketplace.tasks(taskId);

        assertEq(uint256(status), uint256(ComputeMarketplace.TaskStatus.Finalized));
    }
}
