// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

contract AgentRevenueService is Ownable, ReentrancyGuard, Pausable {
    uint256 public constant MIN_PAYMENT = 0.001 ether;
    uint256 public constant PROTOCOL_FEE_BPS = 1000;
    uint256 public constant DISTRIBUTABLE_BPS = 5000;

    address public treasury;
    address public financeDistributor;

    event QueryFulfilled(
        bytes32 indexed queryHash,
        address indexed payer,
        uint256 amount,
        string resultMetadata
    );

    event FeeDistributed(address indexed to, uint256 amount);

    error InsufficientPayment();
    error InvalidAddress();
    error TransferFailed();

    constructor(address _treasury, address _financeDistributor) Ownable(msg.sender) {
        if (_treasury == address(0) || _financeDistributor == address(0)) revert InvalidAddress();
        treasury = _treasury;
        financeDistributor = _financeDistributor;
    }

    function fulfillQuery(string calldata resultMetadata) external payable nonReentrant whenNotPaused {
        if (msg.value < MIN_PAYMENT) revert InsufficientPayment();

        bytes32 queryHash = keccak256(abi.encodePacked(block.timestamp, msg.sender, resultMetadata));

        uint256 protocolFee = (msg.value * PROTOCOL_FEE_BPS) / 10000;
        uint256 distributable = (msg.value * DISTRIBUTABLE_BPS) / 10000;

        (bool okTreasury,) = treasury.call{value: protocolFee}("");
        if (!okTreasury) revert TransferFailed();
        emit FeeDistributed(treasury, protocolFee);

        (bool okDist,) = financeDistributor.call{value: distributable}("");
        if (!okDist) revert TransferFailed();
        emit FeeDistributed(financeDistributor, distributable);

        emit QueryFulfilled(queryHash, msg.sender, msg.value, resultMetadata);
    }

    function setTreasury(address _treasury) external onlyOwner {
        if (_treasury == address(0)) revert InvalidAddress();
        treasury = _treasury;
    }

    function setFinanceDistributor(address _financeDistributor) external onlyOwner {
        if (_financeDistributor == address(0)) revert InvalidAddress();
        financeDistributor = _financeDistributor;
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    receive() external payable {}
}
