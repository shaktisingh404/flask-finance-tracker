from enum import Enum

REDIS_VALID_TTL = 300  # 5 minutes
REDIS_RATE_LIMIT_TTL = 600  # 10 minutes
MIN_NAME_LENGTH = 2
MAX_NAME_LENGTH = 100
MIN_USERNAME_LENGTH = 4
MAX_USERNAME_LENGTH = 50
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 100
MIN_AMOUNT = 0
MAX_AMOUNT = 99999999.99


BUDGET_WARNING_THRESHOLD = 80
BUDGET_EXCEEDED_THRESHOLD = 100
BUDGET_EXCEEDED_KEYWORD = "exceeded"
BUDGET_WARNING_KEYWORD = "warning"
MIN_YEAR = 1900
MAX_YEAR = 2100


class UserRole(Enum):
    ADMIN = "ADMIN"
    USER = "USER"
    CHILD_USER = "CHILD_USER"


class UserGender(Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class SavingPlanStatus(Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"


class Frequency(Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class TransactionType(Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"
