// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "forge-std/Script.sol";
import "../contracts/AgentRevenueService.sol";
import "../contracts/Constitution.sol";

contract DeployScript is Script {
    function run() external {
        address financeDistributor = vm.envAddress("FINANCE_DISTRIBUTOR_ADDRESS");
        address treasury = financeDistributor;

        vm.startBroadcast();

        Constitution constitution = new Constitution();
        AgentRevenueService revenue = new AgentRevenueService(treasury, financeDistributor);

        vm.stopBroadcast();

        console.log("Constitution:", address(constitution));
        console.log("AgentRevenueService:", address(revenue));
    }
}
