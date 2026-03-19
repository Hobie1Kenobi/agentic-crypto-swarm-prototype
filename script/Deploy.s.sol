// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "forge-std/Script.sol";
import "../contracts/AgentRevenueService.sol";
import "../contracts/Constitution.sol";
import "../contracts/ComputeMarketplace.sol";

contract DeployScript is Script {
    function run() external {
        address financeDistributor = vm.envAddress("FINANCE_DISTRIBUTOR_ADDRESS");
        address treasury = vm.envAddress("TREASURY_ADDRESS");

        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        uint256 nonceOverride = vm.envOr("DEPLOY_NONCE", uint256(0));
        if (nonceOverride > 0) {
            vm.setNonce(deployer, uint64(nonceOverride));
            console.log("Deploy nonce override:", nonceOverride);
        } else {
            console.log("Deploy nonce current:", uint64(vm.getNonce(deployer)));
        }

        vm.startBroadcast(deployerPrivateKey);

        Constitution constitution = new Constitution();
        AgentRevenueService revenue = new AgentRevenueService(treasury, financeDistributor);
        ComputeMarketplace marketplace = new ComputeMarketplace(treasury, financeDistributor);

        vm.stopBroadcast();

        console.log("Constitution:", address(constitution));
        console.log("AgentRevenueService:", address(revenue));
        console.log("ComputeMarketplace:", address(marketplace));
    }
}
