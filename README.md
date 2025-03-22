
# Flask Finance Tracker Documentation

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [User Story](#user-story)
- [Modules](#modules)
  - [Authentication Module](#authentication-module)
  - [User Module](#user-module)
  - [Transaction Module](#transaction-module)
  - [Budget Module](#budget-module)
  - [Saving Plan Module](#saving-plan-module)
  - [Category Module](#category-module)
  - [Recurring Transaction Module](#recurring-transaction-module)
  - [Transaction Summary Report Module](#transaction-summary-report-module)
- [Core Components of Transaction Reports](#core-components-of-transaction-reports)
- [Authentication & Security](#authentication--security)
- [Key Relationships](#key-relationships)
- [Implementation Details for Transaction Reports](#implementation-details-for-transaction-reports)
- [Testing](#testing)

## Overview

The Flask Finance Tracker is a personal finance management system built with Flask, SQLAlchemy, and JWT authentication. It leverages Celery for background tasks to empower users with intuitive tools to track transactions, manage budgets, set savings goals, and generate insightful financial reports securely and efficiently. This documentation corresponds to **Version 1.0, March 2025**.

## Prerequisites

- **Python**: 3.9 or higher
- **Flask**: 2.3 or higher
- **Database**: PostgreSQL 15+ (configurable for other databases)
- **Dependencies**: Install via `pip install -r requirements.txt`
- **Celery**: Requires a message broker (e.g., Redis or RabbitMQ)

### Setup
1. Clone the repository: `git clone <repo-url>`
2. Set up environment variables (e.g., `DATABASE_URL`, `JWT_SECRET`, `EMAIL_API_KEY`)
3. Install dependencies: `pip install -r requirements.txt`
4. Run the app: `flask run`

## User Story

As a user of the Finance Tracker application, I want to:

1. **Track financial transactions**
   - Record income and expenses
   - Categorize transactions
   - View transaction history

2. **Manage my user account**
   - Register and verify my email
   - Log in securely
   - Update my profile information and password
   - Create child accounts if I'm a parent

3. **Budget effectively**
   - Create monthly budgets for different categories
   - Track spending against budget limits
   - Receive notifications when approaching budget thresholds

4. **Plan for savings**
   - Set up saving plans with goals and deadlines
   - Track progress toward saving goals
   - Update saving plans as needed

5. **Automate financial tasks**
   - Create recurring transactions
   - Generate financial reports
   - Export transaction data

6. **Use a secure, role-based system**
   - Regular users manage their own finances
   - Parent users oversee child account finances
   - Admin users manage the system

## Modules

### Authentication Module

#### Key Features
- User registration with email verification
- Secure login with JWT tokens
- Password reset functionality
- Admin registration (protected route)

#### API Endpoints

##### POST /api/auth/signup
Register a new user account.

**Request:**
```json
{
  "username": "johndoe",
  "email": "john.doe@example.com",
  "password": "SecurePassword123!",
  "name": "John Doe",
  "gender": "MALE",
  "date_of_birth": "1990-01-15"
}
```

**Response (200 OK):**
```json
{
  "message": "Registration initiated, please check your email for verification"
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": {
      "email": "Missing data for required field."
    }
}

```

##### POST /api/auth/login
Authenticate and receive tokens.

**Request:**
```json
{
  "username": "johndoe",
  "password": "SecurePassword123!"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Notes
- Access tokens expire after 15 minutes; refresh tokens last 30 days.
- Use HTTPS in production to secure token transmission.

### User Module

#### Key Features
- User profile management
- Password and email updates
- Parent-child relationship management
- User account deletion (soft delete)

#### API Endpoints

##### GET /api/users/{user_id}
Get user details.

**Response (200 OK):**
```json
{
  "id": "4c2748c4-a31a-4d06-a034-1e5dfb0b167c",
  "username": "testuser",
  "email": "test@example.com",
  "name": "Test User",
  "gender": "OTHER",
  "date_of_birth": "1995-01-01",
  "role": "USER",
  "created_at": "2025-03-01T12:30:45Z",
  "updated_at": "2025-03-01T12:30:45Z"
}
```

##### PATCH /api/users/{user_id}
Update user profile.

**Request:**
```json
{
  "name": "Updated Name",
  "username": "updateduser",
  "date_of_birth": "1995-05-15",
  "gender": "FEMALE"
}
```

**Response (200 OK):**
```json
{
  "id": "4c2748c4-a31a-4d06-a034-1e5dfb0b167c",
  "username": "updateduser",
  "email": "test@example.com",
  "name": "Updated Name",
  "gender": "FEMALE",
  "date_of_birth": "1995-05-15",
  "role": "USER",
  "created_at": "2025-03-01T12:30:45Z",
  "updated_at": "2025-03-02T10:15:22Z"
}
```

##### POST /api/users/{user_id}/child
Create a child account.

**Request:**
```json
{
  "username": "childuser",
  "name": "Child User",
  "gender": "OTHER",
  "date_of_birth": "2010-05-15"
}
```

**Response (200 OK):**
```json
{
  "message": "Child user created successfully",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Transaction Module

#### Key Features
- Record credits and debits
- Categorize transactions
- Transaction history with pagination
- Link transactions to saving plans

#### API Endpoints

##### GET /api/users/{user_id}/transactions
List transactions with filtering.

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 10)

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "aaba763e-1558-4fe2-93a4-b89e0e986921",
      "user_id": "4c2748c4-a31a-4d06-a034-1e5dfb0b167c",
      "amount": "75.25",
      "transaction_at": "2025-03-01 12:10:10",
      "transaction_type": "DEBIT",
      "description": "Weekly grocery shopping",
      "category": {
        "id": "a7c86a32-a257-44c6-a10e-5b5e15681cc5",
        "name": "Groceries",
        "is_predefined": true
      },
      "category": null,
      "created_at": "2025-03-01T14:32:22Z",
      "updated_at": "2025-03-01T14:32:22Z"
    }
  ],
  "count": 1,
  "next": null,
  "previous": null
}
```

##### POST /api/users/{user_id}/transactions
Create a new transaction.

**Request:**
```json
{
  "title": "Grocery Shopping",
  "amount": 75.25,
  "transaction_date": "2025-03-01",
  "transaction_type": "DEBIT",
  "description": "Weekly grocery shopping",
  "category_id": "a7c86a32-a257-44c6-a10e-5b5e15681cc5"
}
```

**Response (201 Created):**
```json
{
  "id": "aaba763e-1558-4fe2-93a4-b89e0e986921",
  "user_id": "4c2748c4-a31a-4d06-a034-1e5dfb0b167c",
  "title": "Grocery Shopping",
  "amount": "75.25",
  "transaction_date": "2025-03-01",
  "transaction_type": "DEBIT",
  "description": "Weekly grocery shopping",
  "category": {
    "id": "a7c86a32-a257-44c6-a10e-5b5e15681cc5",
    "name": "Groceries",
    "is_predefined": true
  },
  "saving_plan": null,
  "created_at": "2025-03-01T14:32:22Z",
  "updated_at": "2025-03-01T14:32:22Z"
}
```

### Budget Module

#### Key Features
- Create monthly budgets per category
- Track spending against budgets
- Budget history and performance

#### API Endpoints

##### GET /api/users/{user_id}/budgets
List all budgets for a user.

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 10)

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "67e55044-10b1-426f-9247-bb680e5fe0c8",
      "user_id": "4c2748c4-a31a-4d06-a034-1e5dfb0b167c",
      "category": {
              "id": "a7c86a32-a257-44c6-a10e-5b5e15681cc5",
              "name": "Groceries",
              "is_predefined": true
            },
      "amount": "500.00",
      "spent_amount": "325.75",
      "month": 3,
      "year": 2025,
      "created_at": "2025-03-01T00:00:00Z",
      "updated_at": "2025-03-17T10:35:12Z"
    }
  ],
  "count": 1,
  "next": null,
  "previous": null
}
```

##### POST /api/users/{user_id}/budgets
Create a new budget.

**Request:**
```json
{
  "category_id": "a7c86a32-a257-44c6-a10e-5b5e15681cc5",
  "amount": 500.00,
  "month": 3,
  "year": 2025
}
```

**Response (201 Created):**
```json
{
  "id": "67e55044-10b1-426f-9247-bb680e5fe0c8",
  "user_id": "4c2748c4-a31a-4d06-a034-1e5dfb0b167c",
  "category": {
    "id": "a7c86a32-a257-44c6-a10e-5b5e15681cc5",
    "name": "Groceries",
    "is_predefined": true
  },
  "amount": "500.00",
  "spent_amount": "0.00",
  "month": 3,
  "year": 2025,
  "created_at": "2025-03-01T00:00:00Z",
  "updated_at": "2025-03-01T00:00:00Z"
}
```

### Saving Plan Module

#### Key Features
- Set saving goals with deadlines
- Track progress over time
- Flexible saving frequency options

#### API Endpoints

##### GET /api/users/{user_id}/saving_plans
List all saving plans for a user.

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 10)

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "b8f0e372-c79a-48c7-a46b-b3a789c8e94b",
      "user_id": "4c2748c4-a31a-4d06-a034-1e5dfb0b167c",
      "name": "Vacation Fund",
      "amount": "2000.00",
      "saved_amount": "750.00",
      "current_deadline": "2025-12-31",
      "original_deadline": "2025-12-31",
      "frequency": "MONTHLY",
      "status": "ACTIVE",
      "created_at": "2025-01-15T09:30:00Z",
      "updated_at": "2025-03-17T10:35:12Z"
    }
  ],
  "count": 1,
  "next": null,
  "previous": null
}
```

##### POST /api/users/{user_id}/saving_plans
Create a new saving plan.

**Request:**
```json
{
  "name": "Vacation Fund",
  "amount": 2000.00,
  "current_deadline": "2025-12-31",
  "frequency": "MONTHLY"
}
```

**Response (201 Created):**
```json
{
  "id": "b8f0e372-c79a-48c7-a46b-b3a789c8e94b",
  "user_id": "4c2748c4-a31a-4d06-a034-1e5dfb0b167c",
  "name": "Vacation Fund",
  "amount": "2000.00",
  "saved_amount": "0.00",
  "current_deadline": "2025-12-31",
  "original_deadline": "2025-12-31",
  "frequency": "MONTHLY",
  "status": "ACTIVE",
  "created_at": "2025-03-18T14:15:22Z",
  "updated_at": "2025-03-18T14:15:22Z"
}
```

### Category Module

#### Key Features
- System-defined and user-defined categories
- Category management and customization
- Category-based grouping and reporting

#### API Endpoints

##### GET /api/users/{user_id}/categories
List all categories for a user.

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 10)

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "a7c86a32-a257-44c6-a10e-5b5e15681cc5",
      "name": "Groceries",
      "user_id": "4c2748c4-a31a-4d06-a034-1e5dfb0b167c",
      "is_predefined": false,
      "created_at": "2025-03-01T10:00:00Z",
      "updated_at": "2025-03-01T10:00:00Z"
    }
  ],
  "count": 1,
  "next": null,
  "previous": null
}
```

##### POST /api/users/{user_id}/categories
Create a new category.

**Request:**
```json
{
  "name": "Entertainment"
}
```

**Response (201 Created):**
```json
{
  "id": "a8d97b43-b358-45d7-b109-6d7c9ce610c3",
  "name": "Entertainment",
  "user_id": "4c2748c4-a31a-4d06-a034-1e5dfb0b167c",
  "is_predefined": false,
  "created_at": "2025-03-18T14:30:22Z",
  "updated_at": "2025-03-18T14:30:22Z"
}
```

### Recurring Transaction Module

#### Key Features
- Schedule recurring transactions
- Flexible frequency options (e.g., daily, weekly, monthly)
- Automatic execution and tracking

#### API Endpoints

##### GET /api/users/{user_id}/recurring-transactions
List all recurring transactions for a user.

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 10)

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "c5f37587-e939-4da3-8b3a-141e78d9db12",
      "user_id": "4c2748c4-a31a-4d06-a034-1e5dfb0b167c",
      "title": "Rent Payment",
      "amount": "1200.00",
      "type": "DEBIT",
      "description": "Monthly apartment rent",
      "category": {
          "id": "a7c86a32-a257-44c6-a10e-5b5e15681cc5",
          "name": "Groceries",
          "is_predefined": true
        },
      "saving_plan": null,
      "frequency": "MONTHLY",
      "ends_at": "2025-03-01 10:10:10",
      "ends_at": "2025-12-31 10:10:10",
      "next_transaction_at": "2025-04-01 10:10:10",
      "created_at": "2025-02-15T10:35:12Z",
      "updated_at": "2025-03-01T10:35:12Z"
    }
  ],
  "count": 1,
  "next": null,
  "previous": null
}
```

##### POST /api/users/{user_id}/recurring-transactions
Create a new recurring transaction.

**Request:**
```json
{
  "title": "Rent Payment",
  "amount": 1200.00,
  "type": "DEBIT",
  "description": "Monthly apartment rent",
  "category": {
    "id": "a7c86a32-a257-44c6-a10e-5b5e15681cc5",
    "name": "Groceries",
    "is_predefined": true
  },
  "frequency": "MONTHLY",
  "starts_at": "2025-03-01 10:10:10",
  "ends_at": "2025-12-31 10:10:10"
}
```

**Response (201 Created):**
```json
{
  "id": "c5f37587-e939-4da3-8b3a-141e78d9db12",
  "user_id": "4c2748c4-a31a-4d06-a034-1e5dfb0b167c",
  "title": "Rent Payment",
  "amount": "1200.00",
  "type": "DEBIT",
  "description": "Monthly apartment rent",
  "category": {
    "id": "a7c86a32-a257-44c6-a10e-5b5e15681cc5",
    "name": "Groceries",
    "is_predefined": true
  },
  "saving_plan": null,
  "frequency": "MONTHLY",
  "starts_at": "2025-03-01 10:10:10",
  "ends_at": "2025-12-31 10:10:10",
  "next_transaction_at": "2025-04-01 10:10:10",
  "created_at": "2025-03-18T14:45:12Z",
  "updated_at": "2025-03-18T14:45:12Z"
}
```

### Transaction Summary Report Module

#### Key Features
- Generate transaction reports with categorization
- Analyze spending trends across different time periods
- Export transaction data in CSV and PDF formats
- Receive reports via email (processed asynchronously via Celery)

#### API Endpoints

##### GET /api/users/{user_id}/transaction-reports/summary
Generates a detailed transaction summary report.

**Query Parameters:**
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)

**Response (200 OK):**
```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-03-31",
  "total_credit": 7500.00,
  "total_debit": 5250.75,
  "summary": {
    "credit_by_category": [
      {
        "category_id": "a7c86a32-a257-44c6-a10e-5b5e15681cc5",
        "category_name": "Salary",
        "total_amount": 7500.00,
        "transaction_count": 3
      }
    ],
    "debit_by_category": [
      {
        "category_id": "b8d97b43-c358-45d7-b109-6d7c9ce610c3",
        "category_name": "Groceries",
        "total_amount": 950.25,
        "transaction_count": 12
      },
      {
        "category_id": "c5f0e821-d47a-48b9-a12d-3fe6b8c92e4f",
        "category_name": "Rent",
        "total_amount": 3600.00,
        "transaction_count": 3
      }
    ],
    "savings_by_plan": [
      {
        "plan_id": "b8f0e372-c79a-48c7-a46b-b3a789c8e94b",
        "plan_name": "Vacation Fund",
        "total_amount": 1500.00,
        "transaction_count": 3
      }
    ]
  }
}
```

##### GET /api/users/{user_id}/transaction-reports/trends
Generates a spending trends analysis report.

**Query Parameters:**
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)

**Response (200 OK):**
```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-03-31",
  "total_credit": 7500.00,
  "total_debit": 5250.75,
  "categories": [
    {
      "id": "b8d97b43-c358-45d7-b109-6d7c9ce610c3",
      "name": "Groceries",
      "credit": 0.00,
      "debit": 950.25,
      "credit_percentage": 0.00,
      "debit_percentage": 18.10
    },
    {
      "id": "c5f0e821-d47a-48b9-a12d-3fe6b8c92e4f",
      "name": "Rent",
      "credit": 0.00,
      "debit": 3600.00,
      "credit_percentage": 0.00,
      "debit_percentage": 68.56
    }
  ],
  "savings_plan": [
    {
      "id": "b8f0e372-c79a-48c7-a46b-b3a789c8e94b",
      "name": "Vacation Fund",
      "amount": 1500.00,
      "percentage": 100.00
    }
  ]
}
```

##### GET /api/users/{user_id}/transaction-reports/export
Exports transaction history report and sends it via email.

**Query Parameters:**
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)
- `file_format`: Export format (csv or pdf)

**Response (200 OK):**
```json
{
  "message": "Transaction history report will be sent to your email"
}
```

#### Notes
- Reports are queued via Celery and emailed within 5 minutes, subject to email service limits.

## Core Components of Transaction Reports

### TransactionReportService
Handles business logic for generating reports:
1. **get_transaction_report**: Comprehensive transaction summaries
   - Calculates totals by category
   - Handles categorized
   - Processes saving plan transactions
2. **get_trends_report**: Spending trend analysis
   - Shows percentages of total spending
   - Provides savings plan contribution data

### TransactionReport
Handles exportable report generation:
1. **generate_csv**: Creates CSV reports with transaction history, credits/debits, and savings
2. **generate_pdf**: Creates styled PDF reports using ReportLab with tables and metrics

### Background Tasks
Uses Celery for asynchronous processing:
- **email_transaction_history**: Generates and emails reports with retry logic on failure
#### Notes
- Clients should implement retry logic for 500 errors (e.g., exponential backoff).

## Authentication & Security

- **JWT Tokens**: Access tokens (15-minute expiry), refresh tokens (30-day expiry)
- **Best Practices**: Store refresh tokens in HTTP-only cookies; use HTTPS
- **Role-Based Access**: USER, CHILD_USER, ADMIN
- **Parent Oversight**: Parents can view but not modify child resources


## Key Relationships

| Entity          | Relationships                          |
|-----------------|----------------------------------------|
| Users           | Has many transactions, budgets, etc.   |
| Parent Users    | Has many child users                   |
| Transactions    | Belongs to a category                  |
| Budgets         | Tied to categories and time periods   |
| Recurring Trans.| Generates regular transactions         |

## Implementation Details for Transaction Reports

### Report Generation Logic
1. **Transaction Summary**:
   - Filters by user, date range, and optional parameters
   - Separates regular and saving plan transactions
   - Categorizes by type (credit/debit)
   - Calculates totals/subtotals
2. **Trends Analysis**:
   - Calculates percentage distributions
   - Isolates savings contributions
3. **Report Export**:
   - Formats data for CSV/PDF
   - Includes summaries and details

### Transaction Processing
Handles:
- Categorized transactions (credits/debits)
- Uncategorized transactions
- Saving plan contributions

### Data Workflow
1. API request received
2. Query parameters validated
3. Service processes data
4. Response returned
5. Exports queued via Celery


## Testing

- **Unit Tests**: Run `pytest` to execute test suites
- **API Testing**: Use Postman or `curl`:
  ```
  curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "johndoe", "password": "SecurePassword123!"}'
  ```
