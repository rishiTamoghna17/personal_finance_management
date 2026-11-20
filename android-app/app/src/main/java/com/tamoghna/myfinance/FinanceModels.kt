package com.tamoghna.myfinance

internal data class FinanceTransaction(
    val id: String,
    val date: String,
    val type: String,
    val description: String,
    val payee: String,
    val category: String,
    val source: String,
    val destination: String,
    val amountPaise: Long,
)

internal data class AccountBalance(
    val name: String,
    val kind: String,
    val balancePaise: Long,
    val status: String,
)

internal data class GoalProgress(
    val name: String,
    val savedPaise: Long,
    val targetPaise: Long,
    val percent: Int,
    val neededPerMonthPaise: Long?,
    val targetDate: String?,
)

internal data class UpcomingItem(
    val date: String,
    val name: String,
    val type: String,
    val amountPaise: Long,
)

internal data class FinanceAlert(val type: String, val severity: String, val message: String, val link: String? = null)

internal data class ReviewMessage(
    val id: Int,
    val reason: String,
    val sender: String,
    val text: String,
    val sentAt: String,
    val status: String = "open",
    val feedback: String? = null,
)

internal data class CategoryQuestion(
    val id: Int,
    val payee: String,
    val amountPaise: Long,
    val date: String,
    val account: String,
    val suggested: List<String>,
    val choices: List<String>,
)

internal data class TransactionsPage(
    val items: List<FinanceTransaction>,
    val page: Int,
    val totalPages: Int,
    val totalItems: Int,
)

internal data class DashboardData(
    val netWorthPaise: Long,
    val assetsPaise: Long,
    val liabilitiesPaise: Long,
    val accounts: List<AccountBalance>,
    val monthSpendPaise: Long,
    val monthStart: String,
    val monthEnd: String,
    val topCategories: List<Pair<String, Long>>,
    val upcoming: List<UpcomingItem>,
    val transactions: List<FinanceTransaction>,
    val alerts: List<FinanceAlert>,
    val reviewCount: Int,
)

internal data class GoalsData(
    val goals: List<GoalProgress>,
    val upcoming: List<UpcomingItem>,
    val holdingsTotalPaise: Long,
    val holdingsDate: String?,
)

internal data class FeedbackType(val code: String, val title: String)

internal val feedbackTypes = listOf(
    FeedbackType("transaction_alert", "Transaction alert"),
    FeedbackType("promotion", "Promotion"),
    FeedbackType("card_bill_payment", "Card bill payment"),
    FeedbackType("failed_payment", "Failed payment"),
    FeedbackType("refund_reversal", "Refund or reversal"),
    FeedbackType("due_reminder", "Due reminder"),
    FeedbackType("other", "Other"),
)
