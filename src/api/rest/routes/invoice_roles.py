from src.data.models.postgres.enums import UserRole

INVOICE_REVIEW_ROLES = (
    UserRole.FINANCE_ASSOCIATE,
    UserRole.FINANCE_MANAGER,
)

ESCALATION_ROLES = (
    UserRole.FINANCE_ASSOCIATE,
)
