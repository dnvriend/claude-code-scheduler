---
title: Effective Code Documentation for RAG Systems
description: In-depth guide on writing documentation that maximizes Code-RAG retrieval quality
author: Dennis Vriend
date: 2024-12-01
based_on: CodeRAG paper (Li et al., 2024)
source: https://arxiv.org/html/2504.10046v1
tags:
  - code-rag
  - documentation
  - docstrings
  - retrieval-augmented-generation
  - gemini-file-search
  - best-practices
---

# Effective Code Documentation for RAG Systems

A comprehensive guide to writing documentation that maximizes retrieval quality in Code-RAG systems like `gemini-file-search-tool`.

---

## TL;DR

Documentation is **infrastructure for AI**, not just human readability. The CodeRAG paper shows **+40.90 Pass@1 improvement** when documentation enables requirement graphs. Key insight: structured docstrings with explicit purpose, inputs/outputs, and relationships create the semantic anchors that RAG systems need to retrieve the right code.

---

## Table of Contents

1. [Why Documentation Matters for RAG](#why-documentation-matters-for-rag)
2. [The Science: How RAG Uses Documentation](#the-science-how-rag-uses-documentation)
3. [Documentation Hierarchy](#documentation-hierarchy)
4. [Module-Level Documentation](#module-level-documentation)
5. [Class-Level Documentation](#class-level-documentation)
6. [Function-Level Documentation](#function-level-documentation)
7. [Inline Comments for RAG](#inline-comments-for-rag)
8. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
9. [Domain-Specific Terminology](#domain-specific-terminology)
10. [Relationship Documentation](#relationship-documentation)
11. [Examples by Domain](#examples-by-domain)
12. [Measuring Documentation Quality](#measuring-documentation-quality)
13. [Migration Strategy](#migration-strategy)

---

## Why Documentation Matters for RAG

### The Fundamental Problem

When an LLM generates code for a repository, it faces a critical challenge:

```
Query: "Add a function to process refunds"

Without RAG:
  LLM invents → process_refund(amount) → Doesn't match your API

With Poor Documentation RAG:
  Retrieves → random payment files → Missing context

With Good Documentation RAG:
  Retrieves → PaymentProcessor.refund() → Correct integration
```

### Quantified Impact (CodeRAG Paper)

| Documentation Quality | Pass@1 Rate | Delta |
|-----------------------|-------------|-------|
| No RAG (no docs used) | 17.24% | Baseline |
| Text-based RAG (poor docs) | 27.07% | +9.83 |
| Embedding RAG (basic docs) | 40.43% | +23.19 |
| **Bigraph RAG (structured docs)** | **58.14%** | **+40.90** |

The **+17.71 gap** between embedding RAG and bigraph RAG comes from **documentation that enables relationship modeling**.

---

## The Science: How RAG Uses Documentation

### 1. Embedding Generation

RAG systems convert documentation into vector embeddings:

```python
# Poor documentation → Weak embedding
def calc(x, y):
    """Calculate."""  # Embedding: generic, ambiguous
    return x * y * 0.1

# Good documentation → Strong embedding
def calculate_commission(sale_amount: float, rate: float) -> float:
    """Calculate sales commission for a transaction.

    Computes the commission earned by a sales representative
    based on the sale amount and their commission rate tier.
    """  # Embedding: specific, domain-rich, queryable
    return sale_amount * rate
```

### 2. Semantic Similarity Matching

When you query "how to calculate commissions", the RAG system:

1. Embeds your query
2. Finds similar documentation embeddings
3. Returns associated code

**Better documentation = Better embedding = Better matches**

### 3. Requirement Graph Construction

The CodeRAG paper builds a "requirement graph" from documentation:

```
Nodes: Functional descriptions (docstrings)
Edges: Parent-child (calls) and similarity relationships

Example:
  "Process payment"
       ↓ calls
  "Validate amount" + "Execute transaction"
       ↓ similar to
  "Process refund"
```

This graph enables **transitive retrieval**: finding code that's indirectly related but necessary.

---

## Documentation Hierarchy

### Impact by Level

| Level | RAG Impact | Effort | ROI |
|-------|------------|--------|-----|
| Module docstrings | Highest | Low | Excellent |
| Class docstrings | High | Medium | Excellent |
| Function docstrings | High | Medium | Good |
| Inline comments | Medium | High | Moderate |

### Recommended Investment

```
Repository with 100 files, 50 classes, 500 functions:

Priority 1: Module docstrings (100 × 5 min = 8 hours)
Priority 2: Public class docstrings (50 × 10 min = 8 hours)
Priority 3: Public function docstrings (200 × 5 min = 17 hours)
Priority 4: Complex logic comments (as needed)

Total: ~33 hours for major RAG improvement
```

---

## Module-Level Documentation

Module docstrings are the **highest ROI** documentation for RAG because they:
- Provide context for all code in the file
- Enable file-level retrieval (often the first RAG step)
- Establish domain vocabulary

### Template

```python
"""<One-line module purpose>.

<Extended description explaining the module's role in the system>.

This module provides:
- <Capability 1>
- <Capability 2>
- <Capability 3>

Key Components:
- <ClassName>: <brief description>
- <function_name>: <brief description>

Dependencies:
- <internal_module>: <why it's needed>
- <external_package>: <why it's needed>

Related Modules:
- <sibling_module>: <relationship description>

Example:
    >>> from module import MainClass
    >>> obj = MainClass(config)
    >>> result = obj.process(data)

Note:
    <Important considerations, constraints, or gotchas>
"""
```

### Example: Payment Processing Module

```python
"""Payment processing and transaction management.

Handles all payment-related operations including authorization,
capture, refunds, and transaction status tracking. Integrates
with multiple payment gateways through a unified interface.

This module provides:
- Payment authorization and capture
- Refund processing with partial refund support
- Transaction status queries and webhooks
- Payment method tokenization

Key Components:
- PaymentProcessor: Main orchestrator for payment flows
- Transaction: Immutable record of a payment attempt
- Gateway: Abstract interface for payment providers
- RefundManager: Handles refund logic and validations

Dependencies:
- models.customer: Customer and payment method data
- services.fraud: Fraud detection integration
- external.stripe: Stripe API client
- external.paypal: PayPal API client

Related Modules:
- accounting: Ledger entries for completed transactions
- notifications: Customer payment notifications
- reporting: Transaction analytics and reconciliation

Example:
    >>> from payments import PaymentProcessor
    >>> processor = PaymentProcessor(gateway='stripe')
    >>> result = processor.authorize(
    ...     amount=99.99,
    ...     currency='USD',
    ...     customer_id='cust_123'
    ... )
    >>> if result.approved:
    ...     processor.capture(result.transaction_id)

Note:
    All monetary amounts are in the smallest currency unit
    (cents for USD, pence for GBP). Use Decimal for calculations
    to avoid floating-point precision issues.
"""

import logging
from decimal import Decimal
from typing import Optional

from models.customer import Customer, PaymentMethod
from services.fraud import FraudChecker
from external.stripe import StripeClient

logger = logging.getLogger(__name__)
```

### Why This Works for RAG

1. **"Payment processing and transaction management"** - Matches queries about payments
2. **"Refund processing with partial refund support"** - Specific capability matching
3. **"Dependencies: models.customer"** - Enables graph edge creation
4. **"Related Modules: accounting"** - Cross-file relationship for transitive retrieval

---

## Class-Level Documentation

Class docstrings should explain **what the class represents** and **how to use it**.

### Template

```python
class ClassName:
    """<One-line class purpose>.

    <Extended description of the class's role and behavior>.

    Responsibilities:
    - <Responsibility 1>
    - <Responsibility 2>
    - <Responsibility 3>

    Attributes:
        attr1: <description and type context>
        attr2: <description and type context>

    Collaborators:
        <OtherClass>: <how they interact>
        <service_name>: <dependency description>

    State Machine (if applicable):
        PENDING → PROCESSING → COMPLETED
                          ↘ FAILED

    Thread Safety:
        <thread safety guarantees or lack thereof>

    Example:
        >>> obj = ClassName(config)
        >>> obj.setup()
        >>> result = obj.process(input_data)
        >>> obj.cleanup()

    See Also:
        <RelatedClass>: <relationship>
        <helper_function>: <when to use instead>
    """
```

### Example: Transaction Class

```python
class Transaction:
    """Immutable record of a payment attempt.

    Represents a single payment transaction from authorization
    through settlement or failure. Transactions are immutable
    once created; state changes create new TransactionEvent records.

    Responsibilities:
    - Store transaction details (amount, currency, parties)
    - Track transaction state through its lifecycle
    - Provide audit trail via linked events
    - Calculate derived values (fees, net amount)

    Attributes:
        id: Unique transaction identifier (UUID format)
        amount: Transaction amount in smallest currency unit
        currency: ISO 4217 currency code (e.g., 'USD')
        status: Current state (pending, authorized, captured, failed, refunded)
        customer_id: Reference to the paying customer
        merchant_id: Reference to the receiving merchant
        gateway_ref: External reference from payment gateway
        created_at: UTC timestamp of creation
        metadata: Arbitrary key-value pairs for integration data

    Collaborators:
        PaymentProcessor: Creates and updates transactions
        Gateway: Provides external authorization
        Ledger: Records financial impact
        EventStore: Persists state change events

    State Machine:
        PENDING → AUTHORIZED → CAPTURED → SETTLED
                      ↓            ↓
                   VOIDED      REFUNDED (partial or full)
                      ↓            ↓
                   FAILED ←←←←←← FAILED

    Thread Safety:
        Transaction objects are immutable and thread-safe.
        State changes must go through TransactionService.

    Example:
        >>> txn = Transaction(
        ...     amount=1999,  # $19.99 in cents
        ...     currency='USD',
        ...     customer_id='cust_abc',
        ...     merchant_id='merch_xyz'
        ... )
        >>> txn.status
        'pending'
        >>> txn.amount_decimal
        Decimal('19.99')

    See Also:
        TransactionEvent: Individual state changes
        TransactionService: Business logic for state transitions
        RefundTransaction: Specialized refund handling
    """

    def __init__(
        self,
        amount: int,
        currency: str,
        customer_id: str,
        merchant_id: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        ...
```

### Why This Works for RAG

1. **"Immutable record of a payment attempt"** - Clear semantic anchor
2. **"Responsibilities"** - Enumerated capabilities for matching
3. **"Collaborators"** - Explicit graph edges for relationship retrieval
4. **"State Machine"** - Domain logic that helps with "how does X work" queries
5. **"See Also"** - Direct pointers for related code retrieval

---

## Function-Level Documentation

Function docstrings are the **core unit** of Code-RAG retrieval.

### Template

```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """<One-line purpose statement>.

    <Extended description with context and behavior details>.

    Args:
        param1: <description>
            - Constraints: <valid values, ranges>
            - Default behavior: <if optional>
        param2: <description>
            - Format: <expected format if applicable>

    Returns:
        <description of return value>
        - On success: <what's returned>
        - On failure: <what's returned or raised>

    Raises:
        ExceptionType: <when this occurs>
        AnotherException: <when this occurs>

    Calls:
        <function_name>: <why it's called>
        <ClassName.method>: <why it's called>

    Called By:
        <parent_function>: <context>

    Example:
        >>> result = function_name(arg1, arg2)
        >>> print(result)
        expected_output

        # Edge case example
        >>> function_name(None, default_arg)
        Traceback (most recent call last):
            ...
        ValueError: param1 cannot be None

    Note:
        <Important implementation details, performance characteristics>

    See Also:
        <related_function>: <when to use instead>
    """
```

### Example: Authorize Payment Function

```python
def authorize_payment(
    amount: int,
    currency: str,
    customer_id: str,
    payment_method_id: str,
    idempotency_key: str | None = None,
    metadata: dict[str, str] | None = None,
) -> AuthorizationResult:
    """Authorize a payment amount against a customer's payment method.

    Performs a hold on the specified amount without capturing funds.
    The authorization is valid for 7 days (configurable per gateway).
    Use capture_payment() to complete the transaction or void_payment()
    to release the hold.

    This is the first step in a two-phase payment flow (auth + capture),
    commonly used for e-commerce where fulfillment happens after order.

    Args:
        amount: Payment amount in smallest currency unit (cents for USD).
            - Constraints: Must be positive integer, max 99999999
            - Example: 1999 represents $19.99 USD
        currency: ISO 4217 three-letter currency code.
            - Supported: USD, EUR, GBP, CAD, AUD
            - Case-insensitive, normalized to uppercase
        customer_id: Unique customer identifier from your system.
            - Format: String, typically UUID or prefixed ID
        payment_method_id: Tokenized payment method reference.
            - Format: Gateway-specific token (e.g., 'pm_xxx' for Stripe)
            - Must belong to the specified customer
        idempotency_key: Optional key for safe retries.
            - If provided, duplicate requests return cached result
            - Recommended format: UUID or deterministic hash
        metadata: Optional key-value pairs attached to transaction.
            - Max 50 keys, 500 chars per key, 500 chars per value
            - Use for order IDs, session IDs, internal references

    Returns:
        AuthorizationResult containing:
        - transaction_id: Unique identifier for this authorization
        - status: 'authorized', 'declined', or 'pending_review'
        - gateway_ref: External reference for support inquiries
        - authorized_amount: Amount successfully authorized (may differ)
        - decline_reason: Populated if status is 'declined'
        - requires_action: True if 3DS or other verification needed
        - action_url: URL for customer verification (if requires_action)

    Raises:
        InvalidAmountError: If amount <= 0 or exceeds maximum
        InvalidCurrencyError: If currency not in supported list
        CustomerNotFoundError: If customer_id doesn't exist
        PaymentMethodNotFoundError: If payment_method_id invalid
        PaymentMethodExpiredError: If card expired or token invalid
        GatewayError: If payment gateway is unavailable
        FraudDetectedError: If fraud check fails (blocks authorization)

    Calls:
        validate_payment_request: Input validation and normalization
        fraud_service.check: Pre-authorization fraud screening
        gateway.authorize: External gateway API call
        transaction_repo.create: Persist transaction record
        event_publisher.emit: Publish PaymentAuthorized event

    Called By:
        PaymentProcessor.process: Standard payment flow
        CheckoutService.complete: E-commerce checkout
        SubscriptionService.bill: Recurring billing

    Example:
        >>> from payments import authorize_payment
        >>> result = authorize_payment(
        ...     amount=4999,
        ...     currency='USD',
        ...     customer_id='cust_123abc',
        ...     payment_method_id='pm_456def',
        ...     idempotency_key='order_789_auth',
        ...     metadata={'order_id': 'order_789'}
        ... )
        >>> result.status
        'authorized'
        >>> result.transaction_id
        'txn_xyz789'

        # Handling 3D Secure
        >>> result = authorize_payment(amount=10000, ...)
        >>> if result.requires_action:
        ...     redirect_customer(result.action_url)

        # Idempotent retry (same result returned)
        >>> retry_result = authorize_payment(
        ...     amount=4999,
        ...     currency='USD',
        ...     customer_id='cust_123abc',
        ...     payment_method_id='pm_456def',
        ...     idempotency_key='order_789_auth'  # Same key
        ... )
        >>> retry_result.transaction_id == result.transaction_id
        True

    Note:
        - Authorization doesn't guarantee capture will succeed
        - Some gateways may authorize slightly different amounts
        - PCI compliance: Never log full card numbers
        - Performance: Typical latency 200-500ms (gateway-dependent)

    See Also:
        capture_payment: Complete authorized transaction
        void_payment: Cancel authorization and release hold
        charge_payment: Single-step auth + capture (not recommended)
    """
    ...
```

### Why This Works for RAG

1. **Rich semantic content** - Multiple ways to match this function
2. **"Calls" section** - Enables forward graph traversal
3. **"Called By" section** - Enables backward graph traversal
4. **Examples** - Provide usage patterns for generation
5. **"See Also"** - Explicit pointers for related functionality

---

## Inline Comments for RAG

Inline comments have **moderate RAG impact** but are valuable for complex logic.

### When to Use Inline Comments

| Situation | RAG Benefit |
|-----------|-------------|
| Algorithm explanation | Helps match "how does X algorithm work" |
| Business rule | Matches domain-specific queries |
| Workaround/hack | Explains non-obvious code |
| Performance optimization | Matches "optimize X" queries |

### Effective Inline Comments

```python
def calculate_shipping_cost(
    weight_kg: float,
    distance_km: float,
    service_tier: str,
) -> Decimal:
    """Calculate shipping cost based on weight, distance, and service level."""

    # Base rate calculation using tiered pricing model
    # Rates are per-kg and increase with distance brackets
    if distance_km <= 100:
        # Local delivery: flat rate per kg
        base_rate = Decimal("2.50")
    elif distance_km <= 500:
        # Regional delivery: slightly higher rate
        base_rate = Decimal("4.00")
    else:
        # Long-distance: premium rate with fuel surcharge
        base_rate = Decimal("6.50")

    base_cost = base_rate * Decimal(str(weight_kg))

    # Service tier multipliers (from pricing table v2.3)
    # Standard: 1.0x, Express: 1.5x, Overnight: 2.5x
    tier_multipliers = {
        "standard": Decimal("1.0"),
        "express": Decimal("1.5"),
        "overnight": Decimal("2.5"),
    }
    multiplier = tier_multipliers.get(service_tier.lower(), Decimal("1.0"))

    # Dimensional weight adjustment for lightweight bulky items
    # Industry standard: 139 cubic inches per pound (DIM factor)
    # Skip for now - volume not available in this context

    # Minimum charge: $5.00 regardless of calculation
    # Business rule: covers handling costs for small packages
    minimum_charge = Decimal("5.00")

    final_cost = max(base_cost * multiplier, minimum_charge)

    # Round to nearest cent (standard currency rounding)
    return final_cost.quantize(Decimal("0.01"))
```

### Why This Works for RAG

- **"tiered pricing model"** - Matches pricing-related queries
- **"Service tier multipliers"** - Matches tier/level queries
- **"Minimum charge... Business rule"** - Matches business logic queries
- **"Dimensional weight"** - Matches shipping optimization queries

---

## Anti-Patterns to Avoid

### 1. Empty or Trivial Docstrings

```python
# BAD: Adds no information
def process(data):
    """Process the data."""
    ...

# BAD: Just restates the name
def calculate_total(items):
    """Calculate total."""
    ...

# GOOD: Adds context and behavior
def calculate_total(items: list[LineItem]) -> Money:
    """Calculate order total including tax and discounts.

    Sums line item subtotals, applies percentage and fixed
    discounts in order, then adds applicable sales tax
    based on shipping destination.
    """
    ...
```

### 2. Implementation Details Instead of Purpose

```python
# BAD: Describes HOW, not WHAT or WHY
def get_user(user_id):
    """Query database for user record and return User object."""
    ...

# GOOD: Describes purpose and behavior
def get_user(user_id: str) -> User | None:
    """Retrieve a user by their unique identifier.

    Fetches user profile with preferences and permissions.
    Returns None if user doesn't exist (never raises for missing user).
    Results are cached for 5 minutes to reduce database load.
    """
    ...
```

### 3. Outdated Documentation

```python
# BAD: Documentation doesn't match code
def send_email(to: str, subject: str, body: str, cc: list[str] | None = None):
    """Send an email to the specified recipient.

    Args:
        to: Recipient email address
        subject: Email subject line
    """  # Missing: body, cc parameters!
    ...

# GOOD: Keep in sync with signature
def send_email(to: str, subject: str, body: str, cc: list[str] | None = None):
    """Send an email to the specified recipient.

    Args:
        to: Recipient email address (validated for format)
        subject: Email subject line (max 200 chars)
        body: Email body in plain text or HTML
        cc: Optional list of CC recipients
    """
    ...
```

### 4. Missing Relationship Information

```python
# BAD: No context about how this fits in the system
def validate_order(order: Order) -> ValidationResult:
    """Validate an order."""
    ...

# GOOD: Explicit relationships
def validate_order(order: Order) -> ValidationResult:
    """Validate order data before processing.

    Checks inventory availability, price consistency,
    shipping eligibility, and customer credit status.

    Calls:
        inventory_service.check_availability
        pricing_service.verify_prices
        shipping_service.can_ship_to
        credit_service.check_limit

    Called By:
        OrderService.create_order
        CartService.checkout

    See Also:
        validate_line_item: Individual item validation
        validate_customer: Customer-specific validation
    """
    ...
```

### 5. Generic Type Hints Without Context

```python
# BAD: Types without meaning
def process(data: dict, options: dict) -> dict:
    """Process data with options."""
    ...

# GOOD: Meaningful types with documentation
def process_order(
    order_data: OrderInput,
    processing_options: ProcessingConfig,
) -> ProcessingResult:
    """Process an order through the fulfillment pipeline.

    Args:
        order_data: Validated order input containing:
            - customer_id: Customer reference
            - line_items: Products to fulfill
            - shipping_address: Delivery destination
        processing_options: Configuration for this run:
            - priority: 'normal' | 'expedited'
            - notify_customer: Whether to send emails
            - dry_run: Validate without committing

    Returns:
        ProcessingResult with:
            - order_id: Created order identifier
            - status: Processing outcome
            - shipments: Created shipment records
    """
    ...
```

---

## Domain-Specific Terminology

### Why Domain Terms Matter

RAG systems cluster similar concepts. Using consistent domain terminology:
- Improves embedding quality
- Enables cross-file discovery
- Matches user mental models

### Example: E-Commerce Domain

```python
# Establish domain vocabulary in module docstring
"""Order management and fulfillment operations.

Domain Terminology:
- Order: A customer's purchase request (may have multiple shipments)
- Line Item: A single product+quantity within an order
- Shipment: Physical delivery unit (subset of order items)
- Fulfillment: Process of picking, packing, shipping
- Backorder: Items ordered but not in stock
- Split Shipment: Order fulfilled in multiple packages

Order Lifecycle:
    DRAFT → SUBMITTED → PAID → PROCESSING → SHIPPED → DELIVERED
                          ↓
                     CANCELLED / REFUNDED
"""

class Order:
    """A customer's purchase request.

    Represents the commercial transaction between customer and merchant.
    An Order contains one or more LineItems and may result in one or
    more Shipments depending on inventory availability and shipping
    optimization.

    Domain Context:
        In our system, "Order" specifically means a confirmed purchase.
        Use "Cart" for uncommitted selections and "Quote" for B2B pricing.
    """
    ...

def create_shipment(order: Order, line_items: list[LineItem]) -> Shipment:
    """Create a shipment for selected order items.

    Generates a fulfillment unit from a subset of order items.
    Supports split shipments when inventory is distributed or
    items have different shipping requirements.

    Domain Note:
        A single Order may generate multiple Shipments (split shipment).
        Each Shipment has its own tracking number and delivery date.
    """
    ...
```

### Domain Glossary Pattern

For complex domains, include a glossary module:

```python
"""Domain glossary and type definitions.

This module defines the ubiquitous language for the order management
bounded context. All modules should use these terms consistently.

Glossary:
    Order: Customer purchase request (aggregate root)
    LineItem: Product + quantity within an order (entity)
    Shipment: Physical delivery unit (entity)
    Fulfillment: Pick, pack, ship process (domain service)
    Inventory: Available stock by location (aggregate)
    Reservation: Stock held for pending order (entity)
    Backorder: Order for out-of-stock items (state)

Abbreviations:
    SKU: Stock Keeping Unit (product identifier)
    ETA: Estimated Time of Arrival
    SLA: Service Level Agreement
    3PL: Third-Party Logistics provider
"""
```

---

## Relationship Documentation

### The "Calls" and "Called By" Pattern

This is the **highest-impact documentation for RAG** because it enables graph traversal.

```python
def process_checkout(cart: Cart, payment_info: PaymentInfo) -> Order:
    """Process a shopping cart into a completed order.

    Calls:
        validate_cart: Ensure cart is valid for checkout
        calculate_totals: Compute subtotal, tax, shipping
        reserve_inventory: Hold items during payment
        authorize_payment: Secure payment authorization
        create_order: Persist the order record
        send_confirmation: Email customer receipt

    Called By:
        CheckoutController.submit: Web checkout endpoint
        MobileAPI.checkout: Mobile app checkout
        B2BService.place_order: B2B integration
    """
    ...
```

### Explicit Dependency Documentation

```python
class OrderService:
    """Orchestrates order lifecycle operations.

    Dependencies (injected):
        order_repository: Persistence for Order aggregates
        inventory_service: Stock reservation and release
        payment_service: Payment authorization and capture
        notification_service: Customer communications
        event_publisher: Domain event distribution

    Dependency Graph:
        OrderService
            ├── OrderRepository (data)
            ├── InventoryService (business)
            │   └── InventoryRepository (data)
            ├── PaymentService (business)
            │   └── PaymentGateway (external)
            ├── NotificationService (business)
            │   └── EmailProvider (external)
            └── EventPublisher (infrastructure)
    """

    def __init__(
        self,
        order_repository: OrderRepository,
        inventory_service: InventoryService,
        payment_service: PaymentService,
        notification_service: NotificationService,
        event_publisher: EventPublisher,
    ) -> None:
        ...
```

---

## Examples by Domain

### CLI Application

```python
"""CLI command for data export operations.

This module provides the 'export' command group for the CLI.
Supports exporting data in multiple formats with filtering.

Commands:
    export csv: Export to CSV format
    export json: Export to JSON format
    export excel: Export to Excel format

Dependencies:
    cli_client: HTTP client for API calls
    formatters: Output formatting utilities
    validators: Input validation

Related Commands:
    import: Inverse operation (import data)
    query: Interactive data exploration
"""

@click.command()
@click.option("--format", type=click.Choice(["csv", "json", "excel"]))
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--filter", "-f", multiple=True, help="Filter expressions")
def export(format: str, output: str, filter: tuple[str, ...]) -> None:
    """Export data to specified format.

    Fetches data from the API, applies filters, and writes
    to the specified output format. Supports streaming for
    large datasets.

    Args:
        format: Output format (csv, json, excel)
        output: Destination file path (stdout if not specified)
        filter: Zero or more filter expressions (field=value)

    Example:
        # Export all users to CSV
        $ mycli export csv -o users.csv

        # Export filtered data to JSON
        $ mycli export json -f status=active -f role=admin

        # Export to Excel with multiple sheets
        $ mycli export excel -o report.xlsx --include-summary

    Calls:
        cli_client.fetch_data: Retrieve data from API
        apply_filters: Filter data based on expressions
        formatters.write_{format}: Format-specific output

    Called By:
        Main CLI dispatcher
        Scheduled export jobs (via cron wrapper)
    """
    ...
```

### REST API Endpoint

```python
"""Order API endpoints.

Provides RESTful endpoints for order management.
All endpoints require authentication via Bearer token.

Endpoints:
    POST /orders: Create new order
    GET /orders/{id}: Retrieve order by ID
    GET /orders: List orders with pagination
    PUT /orders/{id}: Update order
    DELETE /orders/{id}: Cancel order

Authentication:
    All endpoints require Authorization header
    Scope: orders:read, orders:write

Rate Limits:
    Standard: 100 requests/minute
    Bulk operations: 10 requests/minute
"""

@router.post("/orders", response_model=OrderResponse)
async def create_order(
    request: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """Create a new order from the request payload.

    Validates the order request, reserves inventory, and creates
    the order in PENDING state. Payment is processed separately
    via the /orders/{id}/pay endpoint.

    Args:
        request: Order creation payload containing:
            - line_items: Products and quantities
            - shipping_address: Delivery destination
            - billing_address: Payment address
            - notes: Optional customer notes
        current_user: Authenticated user (from token)
        order_service: Injected order service

    Returns:
        OrderResponse with:
            - id: Created order identifier
            - status: 'pending'
            - total: Calculated order total
            - created_at: Timestamp

    Raises:
        HTTPException 400: Invalid request data
        HTTPException 401: Authentication required
        HTTPException 403: Insufficient permissions
        HTTPException 409: Inventory unavailable
        HTTPException 422: Validation failed

    Calls:
        order_service.create_order: Business logic
        inventory_service.reserve: Stock reservation
        audit_logger.log: Audit trail

    Webhooks:
        Publishes 'order.created' event to configured webhooks

    Example Request:
        POST /orders
        Authorization: Bearer <token>
        Content-Type: application/json

        {
            "line_items": [
                {"product_id": "prod_123", "quantity": 2}
            ],
            "shipping_address": {
                "street": "123 Main St",
                "city": "Seattle",
                "state": "WA",
                "zip": "98101"
            }
        }

    Example Response:
        {
            "id": "order_abc123",
            "status": "pending",
            "total": {"amount": 4999, "currency": "USD"},
            "created_at": "2024-01-15T10:30:00Z"
        }
    """
    ...
```

### Data Model

```python
"""Order data models and schemas.

Defines Pydantic models for order-related data structures.
Used for API request/response validation and serialization.

Models:
    Order: Complete order aggregate
    LineItem: Order line item
    Address: Shipping/billing address
    Money: Currency-safe monetary value

Relationships:
    Order (1) → LineItem (many)
    Order (1) → Address (shipping, billing)
    LineItem (many) → Product (1)
"""

class Order(BaseModel):
    """Complete order aggregate.

    Represents a customer order with all related data.
    This is the aggregate root for the order bounded context.

    Attributes:
        id: Unique order identifier (UUID format)
        customer_id: Reference to ordering customer
        status: Current order state
        line_items: Products in this order
        shipping_address: Delivery destination
        billing_address: Payment address (may match shipping)
        subtotal: Sum of line item prices
        tax: Calculated tax amount
        shipping_cost: Delivery charges
        total: Final order amount
        created_at: Order creation timestamp
        updated_at: Last modification timestamp

    Invariants:
        - total = subtotal + tax + shipping_cost - discounts
        - status transitions follow defined state machine
        - line_items must not be empty

    Serialization:
        - Dates serialized as ISO 8601 strings
        - Money values as integer cents + currency
        - Nested objects fully expanded

    Example:
        >>> order = Order(
        ...     customer_id="cust_123",
        ...     line_items=[LineItem(product_id="prod_1", quantity=2)],
        ...     shipping_address=Address(...)
        ... )
        >>> order.dict()
        {'id': 'order_abc', 'status': 'pending', ...}
    """

    id: str = Field(default_factory=lambda: f"order_{uuid4().hex[:12]}")
    customer_id: str
    status: OrderStatus = OrderStatus.PENDING
    line_items: list[LineItem]
    shipping_address: Address
    billing_address: Address | None = None
    subtotal: Money
    tax: Money
    shipping_cost: Money
    total: Money
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## Measuring Documentation Quality

### Automated Metrics

```python
"""Documentation quality checker.

Analyzes codebase documentation for RAG effectiveness.
Run as: python -m tools.doc_quality src/

Metrics Computed:
- Coverage: % of public symbols with docstrings
- Completeness: % of docstrings with Args/Returns/Raises
- Relationship density: Average Calls/Called By entries
- Domain term usage: Glossary term frequency
"""

def analyze_documentation(module_path: str) -> DocQualityReport:
    """Analyze documentation quality for RAG effectiveness.

    Computes metrics that correlate with RAG retrieval quality
    based on CodeRAG paper findings.

    Returns:
        DocQualityReport with:
            - coverage_score: 0-100 (target: >80)
            - completeness_score: 0-100 (target: >70)
            - relationship_score: 0-100 (target: >50)
            - domain_score: 0-100 (target: >60)
            - overall_score: Weighted average
            - recommendations: Specific improvements
    """
    ...
```

### Quality Checklist

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Module docstring coverage | 100% | All modules have docstrings |
| Public function coverage | >90% | Public functions documented |
| Args/Returns completeness | >80% | Docstrings have full Args section |
| Relationship documentation | >50% | Functions have Calls/Called By |
| Example coverage | >50% | Functions have usage examples |
| Domain term consistency | >80% | Use glossary terms consistently |

---

## Migration Strategy

### Phase 1: High-Impact Modules (Week 1)

1. Identify most-queried modules (from logs or intuition)
2. Add/improve module-level docstrings
3. Document public classes with responsibilities and collaborators

### Phase 2: Core Functions (Week 2-3)

1. Document public API functions fully
2. Add Calls/Called By relationships
3. Include examples for complex functions

### Phase 3: Fill Gaps (Week 4+)

1. Run documentation quality checker
2. Address lowest-scoring modules
3. Add inline comments for complex logic

### Automation Opportunities

```bash
# Generate documentation stubs
python -m tools.doc_stub src/ --output docs/stubs/

# Validate documentation quality
python -m tools.doc_quality src/ --min-score 70

# Generate relationship graph from existing docs
python -m tools.doc_graph src/ --output docs/dependencies.md
```

---

## Summary

### Documentation ROI for RAG

| Investment | Time | RAG Improvement |
|------------|------|-----------------|
| Module docstrings | Low | +15-20% retrieval |
| Class docstrings | Medium | +10-15% retrieval |
| Function docstrings | Medium | +15-25% retrieval |
| Relationship docs (Calls/Called By) | Medium | +20-30% retrieval |
| Domain terminology | Low | +10-15% retrieval |
| Examples | Medium | +5-10% retrieval |

### Key Principles

1. **Document purpose, not implementation** - What and why, not how
2. **Make relationships explicit** - Calls, Called By, See Also
3. **Use domain vocabulary consistently** - Establish and use glossary
4. **Include examples** - Show usage patterns
5. **Keep documentation current** - Outdated docs hurt more than no docs

### The Bottom Line

The CodeRAG paper proves that **documentation is infrastructure for AI-assisted development**. Every hour spent on structured documentation returns multiple hours in improved RAG accuracy, better code generation, and faster onboarding for both humans and AI systems.

---

## References

- CodeRAG Paper: https://arxiv.org/html/2504.10046v1
- Google Style Python Docstrings: https://google.github.io/styleguide/pyguide.html
- NumPy Docstring Standard: https://numpydoc.readthedocs.io/
- Sphinx Documentation: https://www.sphinx-doc.org/
