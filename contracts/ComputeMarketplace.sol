// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract ComputeMarketplace is Ownable, ReentrancyGuard {
    uint256 public constant PROTOCOL_FEE_BPS = 1000; // 10%
    uint256 public constant FINANCE_FEE_BPS = 5000; // 50%
    uint256 public constant MAX_METADATA_LEN = 256;

    address public treasury;
    address public financeDistributor;

    struct Miner {
        address addr;
        string metadata;
        bool registered;
    }
    uint256 public minerCount;
    mapping(address => Miner) public miners;
    address[] public minerList;

    mapping(address => bool) public validators;
    uint256 public legacyRoundId = 1;
    mapping(uint256 => mapping(address => bool)) public legacyValidatorSubmitted;

    mapping(address => uint256) public scores;
    uint256 public totalScoreThisRound;

    event MinerRegistered(address indexed miner, string metadata);
    event ValidatorAllowlisted(address indexed validator, bool allowed);
    event ScoresSubmitted(address indexed validator, address[] miners, uint256[] scores);
    event RewardPaid(address indexed miner, uint256 amount);

    error NotValidator();
    error MinerNotRegistered();
    error InvalidInput();
    error TransferFailed();
    error NoScores();
    error NotRequester();
    error TaskNotFound();
    error InvalidTaskStatus(TaskStatus status);
    error TaskIsExpired();
    error WorkerNotAllowed();
    error ResultAlreadySubmitted();
    error NotWorker();
    error NotEnoughValidators();
    error AlreadySubmitted();
    error InvalidScore();
    error InsufficientPendingWithdrawal();
    error MinerAlreadyRegistered();

    enum TaskStatus {
        None,
        Created,
        Accepted,
        Submitted,
        Finalized,
        Cancelled,
        Expired
    }

    struct Task {
        address requester;
        address assignedWorker;
        uint256 escrowWei;
        string taskMetadata;
        string query;
        bytes32 taskMetadataHash;
        TaskStatus status;
        uint256 createdAt;
        uint256 acceptedAt;
        uint256 submittedAt;
        uint256 deadlineAt;
        uint256 minValidators;
        uint256 minAverageScore;
        uint256 scoreSum;
        uint256 submittedValidators;
        bytes32 resultHash;
        string resultMetadata;
    }

    uint256 public nextTaskId = 1;
    mapping(uint256 => Task) public tasks;
    mapping(uint256 => mapping(address => bool)) public taskValidatorSubmitted;
    mapping(uint256 => mapping(address => uint256)) public taskValidatorScore;
    mapping(uint256 => mapping(address => bytes32)) public taskValidatorNotesHash;
    mapping(address => uint256) public pendingWithdrawals;

    event TaskCreated(
        uint256 indexed taskId,
        address indexed requester,
        address indexed assignedWorker,
        uint256 escrowWei,
        uint256 minValidators,
        uint256 minAverageScore,
        uint256 deadlineAt,
        string taskMetadata,
        string query
    );
    event TaskAccepted(uint256 indexed taskId, address indexed worker);
    event ResultSubmitted(uint256 indexed taskId, address indexed worker, bytes32 resultHash, string resultMetadata);
    event TaskScored(uint256 indexed taskId, address indexed validator, uint256 score, bytes32 notesHash);
    event TaskFinalized(
        uint256 indexed taskId,
        uint256 averageScore,
        uint256 protocolFeeWei,
        uint256 financeFeeWei,
        uint256 workerPayoutWei,
        uint256 requesterRefundWei
    );
    event TaskCancelled(uint256 indexed taskId, address indexed requester, uint256 refundedWei);
    event TaskExpired(uint256 indexed taskId, address indexed requester, uint256 refundedWei);
    event Withdrawn(address indexed who, uint256 amountWei);

    constructor(address _treasury, address _financeDistributor) Ownable(msg.sender) {
        if (_treasury == address(0) || _financeDistributor == address(0)) revert InvalidInput();
        treasury = _treasury;
        financeDistributor = _financeDistributor;
    }

    function registerAsMiner(string calldata metadata) external {
        if (bytes(metadata).length > 256) revert InvalidInput();
        if (miners[msg.sender].registered) revert InvalidInput();
        miners[msg.sender] = Miner({addr: msg.sender, metadata: metadata, registered: true});
        minerList.push(msg.sender);
        minerCount++;
        emit MinerRegistered(msg.sender, metadata);
    }

    function setValidatorAllowlist(address validator, bool allowed) external onlyOwner {
        if (validator == address(0)) revert InvalidInput();
        validators[validator] = allowed;
        emit ValidatorAllowlisted(validator, allowed);
    }

    function submitScores(address[] calldata minerAddresses, uint256[] calldata newScores) external {
        if (!validators[msg.sender]) revert NotValidator();
        if (minerAddresses.length != newScores.length || minerAddresses.length == 0) revert InvalidInput();
        if (legacyValidatorSubmitted[legacyRoundId][msg.sender]) revert AlreadySubmitted();
        legacyValidatorSubmitted[legacyRoundId][msg.sender] = true;
        for (uint256 i = 0; i < minerAddresses.length; i++) {
            if (!miners[minerAddresses[i]].registered) revert MinerNotRegistered();
            scores[minerAddresses[i]] += newScores[i];
            totalScoreThisRound += newScores[i];
        }
        emit ScoresSubmitted(msg.sender, minerAddresses, newScores);
    }

    function distributeRewards() external nonReentrant {
        if (totalScoreThisRound == 0) revert NoScores();
        uint256 balance = address(this).balance;
        if (balance == 0) return;

        uint256 len = minerList.length;
        for (uint256 i = 0; i < len; i++) {
            address m = minerList[i];
            uint256 s = scores[m];
            if (s > 0) {
                uint256 amount = (balance * s) / totalScoreThisRound;
                scores[m] = 0;
                (bool ok,) = m.call{value: amount}("");
                if (ok) emit RewardPaid(m, amount);
            }
        }
        totalScoreThisRound = 0;
        legacyRoundId += 1;
    }

    function getMiners() external view returns (address[] memory addrs, string[] memory metadatas) {
        addrs = new address[](minerList.length);
        metadatas = new string[](minerList.length);
        for (uint256 i = 0; i < minerList.length; i++) {
            addrs[i] = minerList[i];
            metadatas[i] = miners[minerList[i]].metadata;
        }
    }

    function resetRoundScores() external onlyOwner {
        for (uint256 i = 0; i < minerList.length; i++) {
            scores[minerList[i]] = 0;
        }
        totalScoreThisRound = 0;
        legacyRoundId += 1;
    }

    function createTask(
        string calldata taskMetadata,
        string calldata query,
        address assignedWorker,
        uint256 minValidators,
        uint256 minAverageScore,
        uint256 deadlineAt
    ) external payable nonReentrant returns (uint256 taskId) {
        if (msg.value == 0) revert InvalidInput();
        if (bytes(taskMetadata).length > MAX_METADATA_LEN) revert InvalidInput();
        if (bytes(query).length > MAX_METADATA_LEN) revert InvalidInput();
        if (minValidators == 0) revert InvalidInput();
        if (minAverageScore > 100) revert InvalidInput();
        if (deadlineAt <= block.timestamp) revert InvalidInput();
        if (assignedWorker != address(0) && !miners[assignedWorker].registered) revert MinerNotRegistered();

        taskId = nextTaskId++;
        Task storage t = tasks[taskId];
        t.requester = msg.sender;
        t.assignedWorker = assignedWorker;
        t.escrowWei = msg.value;
        t.taskMetadata = taskMetadata;
        t.query = query;
        t.taskMetadataHash = keccak256(abi.encodePacked(taskMetadata, query));
        t.status = TaskStatus.Created;
        t.createdAt = block.timestamp;
        t.acceptedAt = 0;
        t.submittedAt = 0;
        t.deadlineAt = deadlineAt;
        t.minValidators = minValidators;
        t.minAverageScore = minAverageScore;
        t.scoreSum = 0;
        t.submittedValidators = 0;
        emit TaskCreated(
            taskId,
            msg.sender,
            assignedWorker,
            msg.value,
            minValidators,
            minAverageScore,
            deadlineAt,
            taskMetadata,
            query
        );
    }

    function acceptTask(uint256 taskId) external nonReentrant {
        Task storage t = tasks[taskId];
        if (t.requester == address(0)) revert TaskNotFound();
        if (t.status != TaskStatus.Created) revert InvalidTaskStatus(t.status);
        if (block.timestamp > t.deadlineAt) revert TaskIsExpired();
        if (!miners[msg.sender].registered) revert MinerNotRegistered();

        if (t.assignedWorker != address(0) && t.assignedWorker != msg.sender) revert WorkerNotAllowed();
        t.assignedWorker = msg.sender;
        t.status = TaskStatus.Accepted;
        t.acceptedAt = block.timestamp;
        emit TaskAccepted(taskId, msg.sender);
    }

    function submitResult(uint256 taskId, string calldata resultMetadata) external nonReentrant {
        Task storage t = tasks[taskId];
        if (t.requester == address(0)) revert TaskNotFound();
        if (t.status != TaskStatus.Accepted) revert InvalidTaskStatus(t.status);
        if (msg.sender != t.assignedWorker) revert NotWorker();
        if (block.timestamp > t.deadlineAt) revert TaskIsExpired();

        if (bytes(resultMetadata).length > MAX_METADATA_LEN) revert InvalidInput();
        if (t.resultHash != bytes32(0)) revert ResultAlreadySubmitted();

        t.resultMetadata = resultMetadata;
        t.resultHash = keccak256(abi.encodePacked(resultMetadata));
        t.submittedAt = block.timestamp;
        t.status = TaskStatus.Submitted;
        emit ResultSubmitted(taskId, msg.sender, t.resultHash, resultMetadata);
    }

    function submitTaskScore(uint256 taskId, uint256 score, bytes32 notesHash) external nonReentrant {
        Task storage t = tasks[taskId];
        if (t.requester == address(0)) revert TaskNotFound();
        if (t.status != TaskStatus.Submitted) revert InvalidTaskStatus(t.status);
        if (!validators[msg.sender]) revert NotValidator();
        if (score > 100) revert InvalidScore();
        if (taskValidatorSubmitted[taskId][msg.sender]) revert AlreadySubmitted();

        taskValidatorSubmitted[taskId][msg.sender] = true;
        taskValidatorScore[taskId][msg.sender] = score;
        taskValidatorNotesHash[taskId][msg.sender] = notesHash;

        t.scoreSum += score;
        t.submittedValidators += 1;
        emit TaskScored(taskId, msg.sender, score, notesHash);
    }

    function canFinalizeTask(uint256 taskId) public view returns (bool) {
        Task storage t = tasks[taskId];
        if (t.requester == address(0)) return false;
        if (t.status != TaskStatus.Submitted) return false;
        if (block.timestamp > t.deadlineAt) return false;
        return t.submittedValidators >= t.minValidators;
    }

    function finalizeTask(uint256 taskId) external nonReentrant {
        Task storage t = tasks[taskId];
        if (t.requester == address(0)) revert TaskNotFound();
        if (t.status != TaskStatus.Submitted) revert InvalidTaskStatus(t.status);
        if (block.timestamp > t.deadlineAt) revert TaskIsExpired();
        if (t.submittedValidators < t.minValidators) revert NotEnoughValidators();
        // Finalization can be triggered either by the original requester or by an allowlisted validator.
        if (msg.sender != t.requester && !validators[msg.sender]) revert NotValidator();

        uint256 escrowWei = t.escrowWei;
        t.status = TaskStatus.Finalized;
        t.escrowWei = 0;

        uint256 protocolFeeWei = (escrowWei * PROTOCOL_FEE_BPS) / 10000;
        uint256 financeFeeWei = (escrowWei * FINANCE_FEE_BPS) / 10000;
        uint256 workerPoolWei = escrowWei - protocolFeeWei - financeFeeWei;

        uint256 averageScore = t.scoreSum / t.submittedValidators;

        uint256 workerPayoutWei;
        uint256 requesterRefundWei;
        if (averageScore < t.minAverageScore) {
            workerPayoutWei = 0;
            requesterRefundWei = workerPoolWei;
        } else {
            workerPayoutWei = (workerPoolWei * averageScore) / 100;
            if (workerPayoutWei > workerPoolWei) workerPayoutWei = workerPoolWei;
            requesterRefundWei = workerPoolWei - workerPayoutWei;
        }

        pendingWithdrawals[treasury] += protocolFeeWei;
        pendingWithdrawals[financeDistributor] += financeFeeWei;
        pendingWithdrawals[t.assignedWorker] += workerPayoutWei;
        pendingWithdrawals[t.requester] += requesterRefundWei;

        emit TaskFinalized(
            taskId,
            averageScore,
            protocolFeeWei,
            financeFeeWei,
            workerPayoutWei,
            requesterRefundWei
        );
    }

    function cancelTask(uint256 taskId) external nonReentrant {
        Task storage t = tasks[taskId];
        if (t.requester == address(0)) revert TaskNotFound();
        if (msg.sender != t.requester) revert NotRequester();
        if (t.status != TaskStatus.Created && t.status != TaskStatus.Accepted) revert InvalidTaskStatus(t.status);
        if (t.resultHash != bytes32(0)) revert InvalidTaskStatus(t.status);
        if (block.timestamp > t.deadlineAt) revert TaskIsExpired();

        uint256 refundWei = t.escrowWei;
        t.escrowWei = 0;
        t.status = TaskStatus.Cancelled;
        emit TaskCancelled(taskId, msg.sender, refundWei);
        pendingWithdrawals[msg.sender] += refundWei;
    }

    function expireTask(uint256 taskId) external nonReentrant {
        Task storage t = tasks[taskId];
        if (t.requester == address(0)) revert TaskNotFound();
        if (
            t.status == TaskStatus.Finalized ||
            t.status == TaskStatus.Cancelled ||
            t.status == TaskStatus.Expired
        ) revert InvalidTaskStatus(t.status);
        if (block.timestamp <= t.deadlineAt) revert TaskIsExpired();

        uint256 refundWei = t.escrowWei;
        t.escrowWei = 0;
        t.status = TaskStatus.Expired;
        emit TaskExpired(taskId, t.requester, refundWei);
        pendingWithdrawals[t.requester] += refundWei;
    }

    function withdraw() external nonReentrant {
        uint256 amount = pendingWithdrawals[msg.sender];
        if (amount == 0) revert InsufficientPendingWithdrawal();
        pendingWithdrawals[msg.sender] = 0;
        (bool ok,) = msg.sender.call{value: amount}("");
        if (!ok) revert TransferFailed();
        emit Withdrawn(msg.sender, amount);
    }

    receive() external payable {}
}
