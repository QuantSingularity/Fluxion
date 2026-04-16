# Contributing to Fluxion

Thank you for considering contributing to Fluxion! This guide will help you get started with contributing code, documentation, or other improvements.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and professional in all interactions.

### Our Standards

- **Be Respectful**: Treat everyone with respect and consideration
- **Be Collaborative**: Work together and help each other
- **Be Professional**: Keep discussions focused and constructive
- **Be Open**: Welcome newcomers and different viewpoints

## Getting Started

### 1. Fork the Repository

```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/YOUR-USERNAME/Fluxion.git
cd Fluxion

# Add upstream remote
git remote add upstream https://github.com/quantsingularity/Fluxion.git
```

### 2. Set Up Development Environment

```bash
# Run setup script
./scripts/setup_fluxion_env.sh

# Or manually:
# Backend
cd code/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies

# Frontend
cd web-frontend
npm install

# Blockchain
cd code/blockchain
forge install
```

### 3. Create a Branch

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

## Development Workflow

### Branch Naming Convention

| Type          | Prefix      | Example                      |
| ------------- | ----------- | ---------------------------- |
| New feature   | `feature/`  | `feature/flash-loans`        |
| Bug fix       | `fix/`      | `fix/order-validation`       |
| Documentation | `docs/`     | `docs/api-examples`          |
| Performance   | `perf/`     | `perf/query-optimization`    |
| Refactoring   | `refactor/` | `refactor/trading-service`   |
| Tests         | `test/`     | `test/add-integration-tests` |

### Commit Message Format

Follow Conventional Commits specification:

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```bash
git commit -m "feat(trading): add TWAP order support"
git commit -m "fix(api): resolve race condition in order execution"
git commit -m "docs(readme): update installation instructions"
git commit -m "test(pools): add integration tests for liquidity operations"
```

### Keeping Your Fork Updated

```bash
# Fetch upstream changes
git fetch upstream

# Merge into your main branch
git checkout main
git merge upstream/main

# Rebase your feature branch
git checkout feature/your-feature-name
git rebase main
```

## Coding Standards

### Python (Backend)

**Style Guide:** PEP 8

**Tools:**

```bash
# Auto-format code
black code/backend/

# Check style
flake8 code/backend/

# Type checking
mypy code/backend/

# Import sorting
isort code/backend/
```

**Code Example:**

```python
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/order", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    """
    Create a new trading order.

    Args:
        order_data: Order creation data
        db: Database session
        current_user: Authenticated user

    Returns:
        Created order details

    Raises:
        HTTPException: If validation fails or insufficient balance
    """
    # Implementation
    pass
```

**Best Practices:**

- Use type hints for all functions
- Write docstrings for public functions (Google style)
- Keep functions under 50 lines
- Use async/await for I/O operations
- Validate inputs with Pydantic models

### JavaScript/TypeScript (Frontend)

**Style Guide:** Airbnb JavaScript Style Guide

**Tools:**

```bash
# Lint code
npm run lint

# Auto-fix
npm run lint:fix

# Format code
npm run format
```

**Code Example:**

```javascript
import { useState, useEffect } from "react";
import { ethers } from "ethers";

/**
 * Custom hook for interacting with Fluxion contracts
 * @param {string} contractAddress - Contract address
 * @param {Array} abi - Contract ABI
 * @returns {Object} Contract instance and loading state
 */
export const useFluxionContract = (contractAddress, abi) => {
  const [contract, setContract] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initContract = async () => {
      try {
        const provider = new ethers.BrowserProvider(window.ethereum);
        const signer = await provider.getSigner();
        const contractInstance = new ethers.Contract(
          contractAddress,
          abi,
          signer,
        );
        setContract(contractInstance);
      } catch (error) {
        console.error("Failed to initialize contract:", error);
      } finally {
        setLoading(false);
      }
    };

    initContract();
  }, [contractAddress, abi]);

  return { contract, loading };
};
```

**Best Practices:**

- Use functional components with hooks
- Prop-types or TypeScript for type checking
- Extract reusable logic into custom hooks
- Keep components under 200 lines
- Use meaningful variable names

### Solidity (Smart Contracts)

**Style Guide:** Solidity Style Guide

**Tools:**

```bash
# Lint contracts
forge fmt --check

# Auto-format
forge fmt

# Security check
slither code/blockchain/contracts/
```

**Code Example:**

```solidity
// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title FluxionPool
 * @dev Manages liquidity pool with multi-asset support
 */
contract FluxionPool is AccessControl, ReentrancyGuard {
  bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");

  /// @notice Pool configuration structure
  struct PoolConfig {
    address[] assets;
    uint256[] weights;
    uint256 fee;
    bool active;
  }

  /// @notice Emitted when liquidity is added
  event LiquidityAdded(
    address indexed provider,
    uint256 amount,
    uint256 lpTokens
  );

  /**
   * @notice Add liquidity to the pool
   * @param amounts Asset amounts to deposit
   * @return lpTokens LP tokens minted
   */
  function addLiquidity(
    uint256[] calldata amounts
  ) external nonReentrant returns (uint256 lpTokens) {
    // Implementation
  }
}
```

**Best Practices:**

- Use latest stable Solidity version (0.8.19+)
- Include NatSpec comments for all public functions
- Follow checks-effects-interactions pattern
- Use SafeMath for Solidity < 0.8 (built-in in 0.8+)
- Write comprehensive tests (aim for 90%+ coverage)
- Gas optimization (but readability first)

## Testing Requirements

All contributions must include tests. We aim for:

- **Smart Contracts**: 90%+ coverage
- **Backend**: 80%+ coverage
- **Frontend**: 75%+ coverage

### Backend Tests

```bash
# Run all tests
cd code/backend
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_trading.py

# Run with markers
pytest -m "not slow"
```

**Test Example:**

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_order_success(
    client: AsyncClient,
    auth_token: str,
    mock_db: AsyncSession
):
    """Test successful order creation"""
    response = await client.post(
        "/api/v1/order",
        json={
            "asset_id": "BTC-USD",
            "side": "BUY",
            "amount": "1.0",
            "order_type": "MARKET"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PENDING"
    assert data["asset_id"] == "BTC-USD"
```

### Frontend Tests

```bash
# Run tests
cd web-frontend
npm test

# Run with coverage
npm test -- --coverage

# Watch mode
npm test -- --watch
```

**Test Example:**

```javascript
import { render, screen, fireEvent } from "@testing-library/react";
import { OrderForm } from "./OrderForm";

describe("OrderForm", () => {
  it("submits order with correct data", async () => {
    const mockSubmit = jest.fn();
    render(<OrderForm onSubmit={mockSubmit} />);

    fireEvent.change(screen.getByLabelText(/amount/i), {
      target: { value: "1.5" },
    });

    fireEvent.click(screen.getByRole("button", { name: /place order/i }));

    expect(mockSubmit).toHaveBeenCalledWith({
      amount: "1.5",
      // ...
    });
  });
});
```

### Smart Contract Tests

```bash
# Run all tests
cd code/blockchain
forge test

# Run with gas reporting
forge test --gas-report

# Run specific test
forge test --match-test testAddLiquidity

# Run with coverage
forge coverage
```

**Test Example:**

```solidity
// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.19;

import "forge-std/Test.sol";
import "../contracts/LiquidityPool.sol";

contract LiquidityPoolTest is Test {
  LiquidityPool public pool;

  function setUp() public {
    pool = new LiquidityPool();
  }

  function testAddLiquidity() public {
    uint256 amount = 1000e18;

    vm.expectEmit(true, false, false, true);
    emit LiquidityAdded(address(this), amount, amount);

    uint256 lpTokens = pool.addLiquidity(amount);

    assertEq(lpTokens, amount);
    assertEq(pool.balanceOf(address(this)), amount);
  }
}
```

## Documentation

### Code Documentation

- **Python**: Google-style docstrings
- **JavaScript**: JSDoc comments
- **Solidity**: NatSpec comments (@notice, @param, @return)

### Documentation Files

Update relevant documentation when making changes:

- **API changes**: Update `docs/API.md`
- **Configuration**: Update `docs/CONFIGURATION.md`
- **Features**: Update `docs/FEATURE_MATRIX.md`
- **Architecture**: Update `docs/ARCHITECTURE.md`
- **Examples**: Add to `docs/examples/`

### Writing Examples

Include working examples for new features:

```markdown
# Feature Name

Brief description of the feature.

## Example Usage

\`\`\`python
from fluxion_sdk import FluxionClient

client = FluxionClient(api_url="http://localhost:8000")

# Use the feature

result = client.new_feature(param1="value1")
print(result)
\`\`\`

## Expected Output

\`\`\`json
{
"status": "success",
"data": { ... }
}
\`\`\`
```

## Pull Request Process

### 1. Pre-Submit Checklist

- [ ] Code follows project style guide
- [ ] All tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts with main branch

### 2. Create Pull Request

```bash
# Push your branch
git push origin feature/your-feature-name

# Create PR on GitHub
```

**PR Title Format:**

```
<type>: <description>

Example:
feat: Add TWAP order support
fix: Resolve race condition in order execution
docs: Update API documentation with new endpoints
```

**PR Description Template:**

```markdown
## Description

Brief description of changes

## Type of Change

- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## Testing

Describe tests you added/ran

## Checklist

- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Code commented where needed
- [ ] Documentation updated
- [ ] Tests added and passing
- [ ] No new warnings

## Screenshots (if applicable)

Add screenshots for UI changes
```

### 3. Code Review Process

- Maintainers will review your PR
- Address review comments by pushing new commits
- Once approved, your PR will be merged

### 4. After Merge

```bash
# Update your local main
git checkout main
git pull upstream main

# Delete your feature branch
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

## Issue Reporting

### Bug Reports

Use the bug report template:

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce:

1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**

- OS: [e.g. Ubuntu 22.04]
- Browser: [e.g. Chrome 120]
- Version: [e.g. 1.0.0]

**Additional context**
Any other relevant information.
```

### Feature Requests

Use the feature request template:

```markdown
**Is your feature request related to a problem?**
Describe the problem.

**Describe the solution you'd like**
Clear description of desired functionality.

**Describe alternatives you've considered**
Alternative solutions or features.

**Additional context**
Any other relevant information.
```

## Development Tips

### Debugging

```bash
# Backend debugging
cd code/backend
export DEBUG=true
uvicorn app.main:app --reload --log-level debug

# Frontend debugging
cd web-frontend
npm run dev  # Includes React DevTools

# Smart contract debugging
cd code/blockchain
forge test -vvvv  # Very verbose output
```

### Local Development Stack

```bash
# Start database and Redis
docker-compose -f infrastructure/docker-compose.yml up postgres redis

# Start backend with hot reload
cd code/backend
uvicorn app.main:app --reload

# Start frontend with hot reload
cd web-frontend
npm run dev

# Start local blockchain
cd code/blockchain
anvil
```

## Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Documentation**: Check docs/ directory
- **Code Comments**: Read inline comments in code

## Recognition

Contributors will be recognized in:

- `CONTRIBUTORS.md` file
- Release notes
- Project README

Thank you for contributing to Fluxion! 🚀
