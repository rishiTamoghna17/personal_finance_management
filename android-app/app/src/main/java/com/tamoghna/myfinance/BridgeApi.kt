package com.tamoghna.myfinance

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.time.LocalDate

internal class BridgeApi(private val credentials: BridgeCredentials) {
    suspend fun dashboard(): DashboardData = withContext(Dispatchers.IO) {
        val worth = request("GET", "/api/v1/networth")
        val digest = request("GET", "/api/v1/digest")
        val start = LocalDate.now().minusDays(30)
        val end = LocalDate.now()
        val txPage = transactions(start, end, page = 1, limit = 10)
        val alerts = request("GET", "/api/v1/alerts").optJSONArray("alerts") ?: JSONArray()
        val reviews = request("GET", "/api/v1/review").optJSONArray("items") ?: JSONArray()
        val month = digest.optJSONObject("month_to_date") ?: JSONObject()
        val categoriesJson = month.optJSONObject("by_category") ?: JSONObject()
        val categories = categoriesJson.keys().asSequence()
            .map { key -> key to categoriesJson.optLong(key) }
            .sortedByDescending { it.second }
            .take(4)
            .toList()
        DashboardData(
            netWorthPaise = worth.optLong("net_worth_paise"),
            assetsPaise = worth.optLong("assets_paise"),
            liabilitiesPaise = worth.optLong("liabilities_paise"),
            accounts = parseAccounts(worth.optJSONArray("accounts") ?: JSONArray()),
            monthSpendPaise = month.optLong("total_paise"),
            monthStart = month.optString("start"),
            monthEnd = month.optString("end"),
            topCategories = categories,
            upcoming = parseUpcoming(digest.optJSONArray("upcoming_14_days") ?: JSONArray()),
            transactions = txPage.items,
            alerts = parseAlerts(alerts),
            reviewCount = reviews.length(),
        )
    }

    suspend fun transactions(start: LocalDate, end: LocalDate, page: Int, limit: Int): TransactionsPage = withContext(Dispatchers.IO) {
        val query = "?start=$start&end=$end&page=$page&limit=$limit"
        val result = request("GET", "/api/v1/transactions$query")
        val rows = result.optJSONArray("transactions") ?: JSONArray()
        TransactionsPage(
            items = parseTransactions(rows),
            page = result.optInt("page", page),
            totalPages = result.optInt("total_pages", page),
            totalItems = result.optInt("total_items", rows.length()),
        )
    }

    suspend fun goals(): GoalsData = withContext(Dispatchers.IO) {
        val goalRows = request("GET", "/api/v1/goals").optJSONArray("goals") ?: JSONArray()
        val upcomingRows = request("GET", "/api/v1/upcoming?days=30").optJSONArray("items") ?: JSONArray()
        val holdings = request("GET", "/api/v1/holdings")
        GoalsData(
            goals = parseGoals(goalRows),
            upcoming = parseUpcoming(upcomingRows),
            holdingsTotalPaise = holdings.optLong("total_paise"),
            holdingsDate = holdings.optString("statement_date").takeUnless { it == "null" || it.isBlank() },
        )
    }

    suspend fun reviews(): List<ReviewMessage> = withContext(Dispatchers.IO) {
        val rows = request("GET", "/api/v1/review").optJSONArray("items") ?: JSONArray()
        (0 until rows.length()).mapNotNull { index ->
            val item = rows.optJSONObject(index) ?: return@mapNotNull null
            val message = item.optJSONObject("message") ?: JSONObject()
            ReviewMessage(
                id = item.optInt("id"),
                reason = item.optString("reason"),
                sender = message.optString("sender"),
                text = message.optString("text"),
                sentAt = message.optString("sent_at"),
            )
        }
    }

    suspend fun categoryQuestions(): List<CategoryQuestion> = withContext(Dispatchers.IO) {
        val rows = request("GET", "/api/v1/alerts").optJSONArray("alerts") ?: JSONArray()
        (0 until rows.length()).mapNotNull { index ->
            val alert = rows.optJSONObject(index) ?: return@mapNotNull null
            if (alert.optString("type") != "category_needed") return@mapNotNull null
            val data = alert.optJSONObject("data") ?: return@mapNotNull null
            CategoryQuestion(
                id = data.optInt("review_id"), payee = data.optString("payee"),
                amountPaise = data.optLong("amount_paise"), date = data.optString("date"),
                account = data.optString("account"), suggested = data.optJSONArray("suggested").toStringList(),
                choices = data.optJSONArray("choices").toStringList(),
            )
        }
    }

    suspend fun chooseCategory(id: Int, category: String, always: Boolean) = withContext(Dispatchers.IO) {
        request("POST", "/api/v1/review/$id/category", JSONObject()
            .put("category", category).put("always", always))
    }

    suspend fun label(id: Int, label: String) = withContext(Dispatchers.IO) {
        request("POST", "/api/v1/review/$id/feedback", JSONObject().put("label", label))
    }

    suspend fun chat(message: String, history: List<Pair<String, String>>): String = withContext(Dispatchers.IO) {
        val turns = JSONArray()
        history.takeLast(6).forEach { (role, content) ->
            turns.put(JSONObject().put("role", role).put("content", content.take(1000)))
        }
        val response = request("POST", "/api/v1/chat", JSONObject()
            .put("message", message.take(1000))
            .put("history", turns))
        response.optString("answer", "I couldn't get an answer right now.")
    }

    private fun request(method: String, path: String, body: JSONObject? = null): JSONObject {
        val token = credentials.readToken().ifBlank { error("Save the bridge API token first") }
        val base = credentials.serverUrl().trim().trimEnd('/')
        require(base.startsWith("https://")) { "The server address must use private HTTPS" }
        val connection = (URL(base + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 12_000
            readTimeout = 45_000
            setRequestProperty("Authorization", "Bearer $token")
            setRequestProperty("Accept", "application/json")
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
            }
        }
        try {
            if (body != null) connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val content = stream?.use { input -> BufferedReader(InputStreamReader(input)).readText() }.orEmpty()
            if (code !in 200..299) error("Server returned HTTP $code${if (code == 401) " — check the bridge token" else ""}")
            return JSONObject(content)
        } finally {
            connection.disconnect()
        }
    }

    private fun parseTransactions(rows: JSONArray): List<FinanceTransaction> = (0 until rows.length()).mapNotNull { index ->
        val row = rows.optJSONObject(index) ?: return@mapNotNull null
        FinanceTransaction(
            id = row.optString("id"), date = row.optString("date"), type = row.optString("type"),
            description = row.optString("description"), payee = row.optString("payee").takeUnless { it == "null" }.orEmpty(),
            category = row.optString("category").takeUnless { it == "null" }.orEmpty(),
            source = row.optString("source_account").takeUnless { it == "null" }.orEmpty(),
            destination = row.optString("destination_account").takeUnless { it == "null" }.orEmpty(),
            amountPaise = row.optLong("amount_paise"),
        )
    }

    private fun parseAccounts(rows: JSONArray): List<AccountBalance> = (0 until rows.length()).mapNotNull { index ->
        val row = rows.optJSONObject(index) ?: return@mapNotNull null
        AccountBalance(row.optString("name"), row.optString("kind"), row.optLong("balance_paise"), row.optString("balance_status"))
    }

    private fun parseGoals(rows: JSONArray): List<GoalProgress> = (0 until rows.length()).mapNotNull { index ->
        val row = rows.optJSONObject(index) ?: return@mapNotNull null
        GoalProgress(row.optString("name"), row.optLong("saved_paise"), row.optLong("target_paise"),
            row.optInt("percent"), if (row.isNull("needed_per_month_paise")) null else row.optLong("needed_per_month_paise"),
            row.optString("target_date").takeUnless { it == "null" || it.isBlank() })
    }

    private fun parseUpcoming(rows: JSONArray): List<UpcomingItem> = (0 until rows.length()).mapNotNull { index ->
        val row = rows.optJSONObject(index) ?: return@mapNotNull null
        UpcomingItem(row.optString("date"), row.optString("name").takeUnless { it == "null" }.orEmpty(),
            row.optString("type"), row.optLong("amount_paise"))
    }

    private fun parseAlerts(rows: JSONArray): List<FinanceAlert> = (0 until rows.length()).mapNotNull { index ->
        val row = rows.optJSONObject(index) ?: return@mapNotNull null
        val candidate = row.optJSONObject("data")?.optString("link")?.takeIf { it.startsWith("https://") }
        val sameServer = try {
            candidate != null && URI(candidate).host == URI(credentials.serverUrl()).host
        } catch (_: Exception) {
            false
        }
        FinanceAlert(
            row.optString("type"), row.optString("severity"), row.optString("message"),
            candidate.takeIf { sameServer },
        )
    }

    private fun JSONArray?.toStringList(): List<String> = this?.let { values ->
        (0 until values.length()).mapNotNull { values.optString(it).takeIf(String::isNotBlank) }
    }.orEmpty()
}
