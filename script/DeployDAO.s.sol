// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "forge-std/Script.sol";
import "../contracts/AgentRevenueService.sol";
import "../contracts/SwarmGovernanceToken.sol";
import "../contracts/SwarmGovernor.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";
import "@openzeppelin/contracts/governance/utils/IVotes.sol";

contract DeployDAOScript is Script {
    function run() external {
        address revenueAddress = vm.envAddress("REVENUE_SERVICE_ADDRESS");

        vm.startBroadcast();

        SwarmGovernanceToken token = new SwarmGovernanceToken();
        address[] memory proposers = new address[](1);
        proposers[0] = msg.sender;
        address[] memory executors = new address[](1);
        executors[0] = msg.sender;
        TimelockController timelock = new TimelockController(60, proposers, executors, msg.sender);
        SwarmGovernor governor = new SwarmGovernor(IVotes(address(token)), timelock);

        timelock.grantRole(timelock.PROPOSER_ROLE(), address(governor));
        timelock.grantRole(timelock.EXECUTOR_ROLE(), address(governor));
        timelock.grantRole(timelock.CANCELLER_ROLE(), address(governor));
        timelock.revokeRole(timelock.PROPOSER_ROLE(), msg.sender);
        timelock.revokeRole(timelock.EXECUTOR_ROLE(), msg.sender);
        timelock.revokeRole(timelock.CANCELLER_ROLE(), msg.sender);

        AgentRevenueService revenue = AgentRevenueService(payable(revenueAddress));
        revenue.transferOwnership(address(timelock));

        vm.stopBroadcast();

        console.log("SwarmGovernanceToken:", address(token));
        console.log("TimelockController:", address(timelock));
        console.log("SwarmGovernor:", address(governor));
        console.log("AgentRevenueService owner -> Timelock");
    }
}
