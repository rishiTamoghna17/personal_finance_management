package com.tamoghna.myfinance

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.zIndex
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.math.BigDecimal
import java.net.SocketTimeoutException
import java.time.LocalDate
import java.util.Currency
import java.util.Locale

private val LedgerGreen = Color(0xFF176B4D)
private val LedgerGreenDark = Color(0xFF104B38)
private val WarmCanvas = Color(0xFFF7F6F1)
private val SoftGreen = Color(0xFFE8F1EA)
private val AccentOrange = Color(0xFFE87722)
private val MutedText = Color(0xFF64716A)

private enum class AppTab(val title: String, val glyph: String) {
    Home("Home", "⌂"), Transactions("Activity", "↕"), Goals("Plans", "◎"), Chat("Ask", "✦"), Review("Review", "☷")
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val credentials = BridgeCredentials(this)
        setContent {
            MaterialTheme(
                colorScheme = lightColorScheme(
                    primary = LedgerGreen,
                    onPrimary = Color.White,
                    secondary = AccentOrange,
                    background = WarmCanvas,
                    surface = Color.White,
                    onSurface = Color(0xFF18231E),
                ),
            ) { FinanceApp(credentials) }
        }
    }
}

@Composable
private fun FinanceApp(credentials: BridgeCredentials) {
    val uriHandler = LocalUriHandler.current
    val api = remember(credentials) { BridgeApi(credentials) }
    val scope = rememberCoroutineScope()
    var tab by remember { mutableStateOf(AppTab.Home) }
    var dashboard by remember { mutableStateOf<DashboardData?>(null) }
    var transactionPage by remember { mutableStateOf<TransactionsPage?>(null) }
    var goalsData by remember { mutableStateOf<GoalsData?>(null) }
    val reviews = remember { mutableStateListOf<ReviewMessage>() }
    val categoryQuestions = remember { mutableStateListOf<CategoryQuestion>() }
    val chat = remember { mutableStateListOf<Pair<String, String>>() }
    var server by remember { mutableStateOf(credentials.serverUrl()) }
    var tokenInput by remember { mutableStateOf("") }
    var messageInput by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var showSettings by remember { mutableStateOf(!credentials.hasToken()) }
    var errorMessage by remember { mutableStateOf("") }
    var connectionMessage by remember { mutableStateOf("") }

    fun runRequest(action: suspend () -> Unit) {
        if (busy) return
        busy = true
        errorMessage = ""
        scope.launch {
            try {
                action()
            } catch (error: Exception) {
                errorMessage = if (error is SocketTimeoutException) {
                    "The server timed out. Check that Tailscale is connected, then tap Refresh."
                } else {
                    error.message ?: "The request failed. Check the server connection and try again."
                }
            } finally {
                busy = false
            }
        }
    }

    fun loadHome() = runRequest { dashboard = api.dashboard() }
    fun loadTransactions(page: Int = 1) = runRequest {
        transactionPage = api.transactions(LocalDate.now().minusDays(90), LocalDate.now(), page, 50)
    }
    fun loadGoals() = runRequest { goalsData = api.goals() }
    fun loadReviews() = runRequest {
        val fresh = api.reviews()
        val categories = api.categoryQuestions()
        reviews.clear()
        reviews.addAll(fresh)
        categoryQuestions.clear()
        categoryQuestions.addAll(categories)
    }

    fun select(next: AppTab) {
        tab = next
        when (next) {
            AppTab.Home -> if (dashboard == null && credentials.hasToken()) loadHome()
            AppTab.Transactions -> if (transactionPage == null && credentials.hasToken()) loadTransactions()
            AppTab.Goals -> if (goalsData == null && credentials.hasToken()) loadGoals()
            AppTab.Review -> if (credentials.hasToken()) loadReviews()
            AppTab.Chat -> Unit
        }
    }

    Scaffold(
        containerColor = WarmCanvas,
        bottomBar = {
            NavigationBar(containerColor = Color.White) {
                AppTab.entries.forEach { destination ->
                    NavigationBarItem(
                        selected = tab == destination,
                        onClick = { select(destination) },
                        icon = { Text(destination.glyph, style = MaterialTheme.typography.titleLarge) },
                        label = { Text(destination.title) },
                    )
                }
            }
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(start = 20.dp, end = 14.dp, top = 15.dp, bottom = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text("MY FINANCE", color = LedgerGreen, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold)
                    Text(tab.title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = LedgerGreenDark)
                }
                TextButton(onClick = { showSettings = !showSettings }) { Text(if (showSettings) "Close" else "⚙ Setup") }
                TextButton(enabled = !busy && credentials.hasToken(), onClick = {
                    when (tab) {
                        AppTab.Home -> loadHome()
                        AppTab.Transactions -> loadTransactions()
                        AppTab.Goals -> loadGoals()
                        AppTab.Review -> loadReviews()
                        AppTab.Chat -> Unit
                    }
                }) { Text(if (busy) "Loading…" else "Refresh") }
            }

            if (showSettings) {
                ConnectionCard(
                    server = server,
                    token = tokenInput,
                    saved = credentials.hasToken(),
                    busy = busy,
                    onServer = { server = it },
                    onToken = { tokenInput = it },
                    onSave = {
                        val cleaned = server.trim().trimEnd('/')
                        when {
                            !cleaned.startsWith("https://") -> errorMessage = "Use the private HTTPS address beginning with https://"
                            tokenInput.isBlank() && !credentials.hasToken() -> errorMessage = "Paste the bridge API token first"
                            else -> {
                                credentials.setServerUrl(cleaned)
                                if (tokenInput.isNotBlank()) credentials.saveToken(tokenInput.trim())
                                tokenInput = ""
                                showSettings = false
                                connectionMessage = "Connection details saved securely on this phone."
                                loadHome()
                            }
                        }
                    },
                )
            }

            if (connectionMessage.isNotBlank() && !showSettings) {
                Text(connectionMessage, modifier = Modifier.padding(horizontal = 20.dp, vertical = 4.dp), color = LedgerGreen, style = MaterialTheme.typography.bodySmall)
            }
            if (errorMessage.isNotBlank()) {
                Surface(color = Color(0xFFFFE8E4), modifier = Modifier.fillMaxWidth()) {
                    Text(errorMessage, modifier = Modifier.padding(horizontal = 20.dp, vertical = 9.dp), color = Color(0xFF8B3023), style = MaterialTheme.typography.bodySmall)
                }
            }

            when (tab) {
                AppTab.Home -> HomeScreen(
                    dashboard, busy,
                    onTransactions = { select(AppTab.Transactions) },
                    onReviews = { select(AppTab.Review) },
                    onReconnect = { link -> uriHandler.openUri(link) },
                )
                AppTab.Transactions -> TransactionsScreen(transactionPage, busy, onPage = { loadTransactions(it) })
                AppTab.Goals -> GoalsScreen(goalsData, busy)
                AppTab.Chat -> ChatScreen(chat, messageInput, busy, onInput = { messageInput = it }, onSend = {
                    val prompt = messageInput.trim()
                    if (prompt.isNotEmpty() && !busy) {
                        val history = chat.toList()
                        chat.add("user" to prompt)
                        messageInput = ""
                        runRequest {
                            val reply = api.chat(prompt, history)
                            chat.add("assistant" to reply)
                        }
                    }
                })
                AppTab.Review -> ReviewScreen(
                    reviews = reviews,
                    categories = categoryQuestions,
                    busy = busy,
                    onLabel = { item, label -> runRequest {
                        api.label(item.id, label.code)
                        val fresh = api.reviews()
                        reviews.clear()
                        reviews.addAll(fresh)
                        connectionMessage = "Saved your correction: ${label.title}."
                    } },
                    onCategory = { question, category, always -> runRequest {
                        api.chooseCategory(question.id, category, always)
                        val updatedReviews = api.reviews()
                        val updatedCategories = api.categoryQuestions()
                        reviews.clear()
                        reviews.addAll(updatedReviews)
                        categoryQuestions.clear()
                        categoryQuestions.addAll(updatedCategories)
                        connectionMessage = if (always) "Category saved and future payments to this payee will use it." else "Category saved to this payment."
                    } },
                )
            }
        }
    }
}

@Composable
private fun ConnectionCard(
    server: String,
    token: String,
    saved: Boolean,
    busy: Boolean,
    onServer: (String) -> Unit,
    onToken: (String) -> Unit,
    onSave: () -> Unit,
) {
    ElevatedCard(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.elevatedCardColors(containerColor = Color.White),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Private server", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                Surface(shape = RoundedCornerShape(40), color = SoftGreen) {
                    Text("HTTPS", modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp), color = LedgerGreen, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                }
            }
            OutlinedTextField(
                value = server,
                onValueChange = onServer,
                label = { Text("Tailscale server address") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
            )
            OutlinedTextField(
                value = token,
                onValueChange = onToken,
                label = { Text("Bridge API token") },
                placeholder = { Text(if (saved) "Already saved securely on this phone" else "Paste your token") },
                singleLine = true,
                visualTransformation = PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth(),
            )
            Button(enabled = !busy, onClick = onSave, modifier = Modifier.fillMaxWidth()) {
                Text(if (saved) "Save connection" else "Connect securely")
            }
        }
    }
}

@Composable
private fun HomeScreen(
    data: DashboardData?, busy: Boolean, onTransactions: () -> Unit, onReviews: () -> Unit,
    onReconnect: (String) -> Unit,
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Column(Modifier.padding(top = 5.dp, bottom = 2.dp)) {
                Text("A clear view of your money", style = MaterialTheme.typography.bodyMedium, color = MutedText)
            }
        }
        if (data == null) {
            item { EmptyCard("Connect to your finance server", "Save your private server address and bridge token using Setup above.") }
        } else {
            item {
                ElevatedCard(
                    shape = RoundedCornerShape(26.dp),
                    colors = CardDefaults.elevatedCardColors(containerColor = LedgerGreenDark),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                        Text("NET WORTH", color = Color(0xFFCDE2D3), style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold)
                        Text(formatInr(data.netWorthPaise), color = Color.White, style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
                        Text("Assets minus liabilities · ledger values", color = Color(0xFFDCEAE0), style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    SummaryCard("Assets", data.assetsPaise, Modifier.weight(1f))
                    SummaryCard("Liabilities", data.liabilitiesPaise, Modifier.weight(1f))
                }
            }
            item {
                ElevatedCard(shape = RoundedCornerShape(22.dp), modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(17.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("Spent this month", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        Text(formatInr(data.monthSpendPaise), style = MaterialTheme.typography.headlineSmall, color = LedgerGreenDark, fontWeight = FontWeight.Bold)
                        Text("${data.monthStart} to ${data.monthEnd}", style = MaterialTheme.typography.labelSmall, color = MutedText)
                        data.topCategories.take(3).forEach { (name, amount) ->
                            Row(Modifier.fillMaxWidth().padding(top = 5.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(name, style = MaterialTheme.typography.bodySmall, color = MutedText)
                                Text(formatInr(amount), style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Medium)
                            }
                        }
                    }
                }
            }
            val cards = data.accounts.filter { it.kind == "credit_card" }
            val otherAccounts = data.accounts.filterNot { it.kind == "credit_card" }
            item {
                SectionHeading("Cards", "${cards.size} in your wallet")
                if (cards.isEmpty()) EmptyCard("No credit cards yet", "Cards from Firefly will appear here.")
            }
            if (cards.isNotEmpty()) item { CreditCardStack(cards) }
            item {
                SectionHeading("Bank accounts", "${otherAccounts.size} · balances from Firefly")
                if (otherAccounts.isEmpty()) EmptyCard("No bank accounts yet", "Bank and cash accounts will appear here.")
            }
            items(otherAccounts, key = { it.name }) { account ->
                ElevatedCard(shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) {
                    Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 13.dp), verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(account.name, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                            Text("${account.kind.replace('_', ' ')} · ${account.status}", style = MaterialTheme.typography.labelSmall, color = MutedText)
                        }
                        Text(formatInr(account.balancePaise), fontWeight = FontWeight.SemiBold)
                    }
                }
            }
            item {
                SectionHeading("Recent activity", "Last 30 days")
                if (data.transactions.isEmpty()) EmptyCard("No transactions in this period", "The ledger has no recent INR transactions to show.")
            }
            items(data.transactions.take(5), key = { it.id }) { TransactionCard(it) }
            item {
                OutlinedButton(onClick = onTransactions, modifier = Modifier.fillMaxWidth()) { Text("See all activity") }
            }
            item {
                SectionHeading("Needs attention", "${data.reviewCount} open review items")
                if (data.alerts.isEmpty() && data.reviewCount == 0) EmptyCard("All caught up", "There are no active alerts right now.")
                data.alerts.take(4).forEach { alert -> AlertCard(alert, onReconnect) }
            }
            item { OutlinedButton(onClick = onReviews, modifier = Modifier.fillMaxWidth()) { Text("Open review inbox") } }
            item { Spacer(Modifier.height(8.dp)) }
        }
        if (busy && data == null) item { LoadingCard() }
    }
}

@Composable
private fun CreditCardStack(cards: List<AccountBalance>) {
    var activeIndex by remember(cards) { mutableStateOf(0) }
    val ordered = cards.indices.map { cards[(activeIndex + it) % cards.size] }
    val peek = 42
    val faceHeight = 174
    Box(Modifier.fillMaxWidth().height((faceHeight + peek * (cards.size - 1)).dp)) {
        ordered.indices.reversed().forEach { stackIndex ->
            val card = ordered[stackIndex]
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(faceHeight.dp)
                    .offset(y = (peek * stackIndex).dp)
                    .zIndex((ordered.size - stackIndex).toFloat())
                    .shadow(if (stackIndex == 0) 12.dp else 3.dp, RoundedCornerShape(23.dp))
                    .clip(RoundedCornerShape(23.dp))
                    .background(cardBrush(card.name))
                    .then(if (stackIndex == 0) Modifier.clickable { activeIndex = (activeIndex + 1) % cards.size } else Modifier)
            ) {
                Box(Modifier.fillMaxSize()) {
                    Box(
                        Modifier.size(170.dp).align(Alignment.TopEnd).offset(x = 50.dp, y = (-55).dp)
                            .background(Color.White.copy(alpha = 0.09f), CircleShape)
                    )
                    Box(
                        Modifier.size(120.dp).align(Alignment.BottomStart).offset(x = 45.dp, y = 45.dp)
                            .background(Color.Black.copy(alpha = 0.08f), CircleShape)
                    )
                    Column(
                        Modifier.fillMaxSize().padding(horizontal = 18.dp, vertical = 15.dp),
                        verticalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(Modifier.size(width = 34.dp, height = 25.dp).clip(RoundedCornerShape(6.dp)).background(Color(0xFFD9C58C)))
                            Text(
                                "  ${card.name.substringBefore(' ').uppercase()}",
                                color = Color.White.copy(alpha = 0.9f),
                                style = MaterialTheme.typography.labelLarge,
                                fontWeight = FontWeight.Bold,
                            )
                            Spacer(Modifier.weight(1f))
                            Text("CREDIT", color = Color.White.copy(alpha = 0.76f), style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                        }
                        Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                            Text(card.name, color = Color.White, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Bottom) {
                                Column(Modifier.weight(1f)) {
                                    Text("LEDGER BALANCE", color = Color.White.copy(alpha = 0.72f), style = MaterialTheme.typography.labelSmall)
                                    Text(formatInr(card.balancePaise), color = Color.White, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                                }
                                if (stackIndex == 0) Text("${activeIndex + 1}/${cards.size}  ›", color = Color.White.copy(alpha = 0.85f), style = MaterialTheme.typography.labelLarge)
                            }
                        }
                    }
                }
            }
        }
    }
}

private fun cardBrush(name: String): Brush {
    val palette = when {
        name.contains("HDFC", ignoreCase = true) -> listOf(Color(0xFF163960), Color(0xFF2877AA))
        name.contains("Axis", ignoreCase = true) -> listOf(Color(0xFF111820), Color(0xFF394554))
        name.contains("ICICI", ignoreCase = true) -> listOf(Color(0xFF084576), Color(0xFF1682AD))
        name.contains("SBI", ignoreCase = true) -> listOf(Color(0xFF062C58), Color(0xFF0870A8))
        else -> listOf(LedgerGreenDark, LedgerGreen)
    }
    return Brush.linearGradient(palette)
}

@Composable
private fun TransactionsScreen(page: TransactionsPage?, busy: Boolean, onPage: (Int) -> Unit) {
    LazyColumn(Modifier.fillMaxSize().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Text("INR ledger activity from the last 90 days", modifier = Modifier.padding(top = 5.dp, bottom = 2.dp), style = MaterialTheme.typography.bodySmall, color = MutedText)
        }
        if (page == null) {
            item { EmptyCard("Load your activity", "Transactions are read from the Firefly ledger.") }
            if (busy) item { LoadingCard() }
        } else if (page.items.isEmpty()) {
            item { EmptyCard("No INR transactions found", "Try refreshing after new activity arrives in Firefly.") }
        } else {
            items(page.items, key = { it.id }) { TransactionCard(it, expanded = true) }
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Text("${page.totalItems} entries · page ${page.page} of ${page.totalPages}", style = MaterialTheme.typography.labelSmall, color = MutedText)
                    Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                        TextButton(enabled = !busy && page.page > 1, onClick = { onPage(page.page - 1) }) { Text("Previous") }
                        TextButton(enabled = !busy && page.page < page.totalPages, onClick = { onPage(page.page + 1) }) { Text("Next") }
                    }
                }
            }
        }
        item { Spacer(Modifier.height(8.dp)) }
    }
}

@Composable
private fun GoalsScreen(data: GoalsData?, busy: Boolean) {
    LazyColumn(Modifier.fillMaxSize().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(11.dp)) {
        item { Text("Savings goals, investment values and upcoming dues", modifier = Modifier.padding(top = 5.dp), style = MaterialTheme.typography.bodySmall, color = MutedText) }
        if (data == null) {
            item { EmptyCard("Load your plans", "Goals and holdings are read from your finance server.") }
            if (busy) item { LoadingCard() }
        } else {
            item { SectionHeading("Goals", "${data.goals.size} tracked") }
            if (data.goals.isEmpty()) item { EmptyCard("No goals yet", "Your Firefly savings goals will show here when configured.") }
            items(data.goals, key = { it.name }) { goal -> GoalCard(goal) }
            item { SectionHeading("Investments", data.holdingsDate?.let { "CAS values · $it" } ?: "No CAS imported") }
            item {
                ElevatedCard(shape = RoundedCornerShape(20.dp), modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(17.dp)) {
                        Text(formatInr(data.holdingsTotalPaise), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = LedgerGreenDark)
                        Text("Value from the latest statement", style = MaterialTheme.typography.bodySmall, color = MutedText)
                    }
                }
            }
            item { SectionHeading("Upcoming", "Next 30 days") }
            if (data.upcoming.isEmpty()) item { EmptyCard("No upcoming dues", "No EMI or card bill is scheduled in this period.") }
            items(data.upcoming, key = { "${it.type}-${it.date}-${it.name}" }) { UpcomingCard(it) }
        }
        item { Spacer(Modifier.height(8.dp)) }
    }
}

@Composable
private fun ChatScreen(
    messages: List<Pair<String, String>>,
    input: String,
    busy: Boolean,
    onInput: (String) -> Unit,
    onSend: () -> Unit,
) {
    Column(Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
        Text("Ask about your ledger, goals or spending. Answers use the private advisor API.", modifier = Modifier.padding(top = 4.dp, bottom = 9.dp), style = MaterialTheme.typography.bodySmall, color = MutedText)
        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            if (messages.isEmpty()) item { EmptyCard("Your finance assistant", "Try asking: ‘How much did I spend this month?’") }
            items(messages.size) { index ->
                val (role, content) = messages[index]
                ChatBubble(role, content)
            }
            if (busy) item { LoadingCard() }
        }
        Row(Modifier.fillMaxWidth().padding(vertical = 10.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(
                value = input,
                onValueChange = onInput,
                modifier = Modifier.weight(1f),
                label = { Text("Ask a question") },
                maxLines = 3,
            )
            Button(enabled = input.isNotBlank() && !busy, onClick = onSend) { Text("Send") }
        }
    }
}

@Composable
private fun ReviewScreen(
    reviews: List<ReviewMessage>,
    categories: List<CategoryQuestion>,
    busy: Boolean,
    onLabel: (ReviewMessage, FeedbackType) -> Unit,
    onCategory: (CategoryQuestion, String, Boolean) -> Unit,
) {
    LazyColumn(Modifier.fillMaxSize().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item { Text("Categorize payments and correct unclear messages", modifier = Modifier.padding(top = 4.dp), style = MaterialTheme.typography.bodySmall, color = MutedText) }
        if (categories.isNotEmpty()) item { SectionHeading("Payment categories", "${categories.size} waiting") }
        items(categories, key = { "category-${it.id}" }) { question ->
            CategoryQuestionCard(question, busy) { name, always -> onCategory(question, name, always) }
        }
        if (reviews.isNotEmpty()) item { SectionHeading("Message review", "Corrections guide future local classification") }
        if (reviews.isEmpty() && categories.isEmpty()) {
            item { EmptyCard("Nothing needs review", "Unparsed messages and uncategorized payments will appear here.") }
            if (busy) item { LoadingCard() }
        } else {
            items(reviews, key = { "message-${it.id}" }) { item -> ReviewCard(item, busy) { label -> onLabel(item, label) } }
        }
        item { Spacer(Modifier.height(8.dp)) }
    }
}

@Composable
private fun CategoryQuestionCard(question: CategoryQuestion, enabled: Boolean, onApply: (String, Boolean) -> Unit) {
    var menuOpen by remember(question.id) { mutableStateOf(false) }
    var selected by remember(question.id) { mutableStateOf(question.suggested.firstOrNull().orEmpty()) }
    var always by remember(question.id) { mutableStateOf(false) }
    ElevatedCard(shape = RoundedCornerShape(20.dp), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(question.payee.ifBlank { "Uncategorized payment" }, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            Text("${formatInr(question.amountPaise)} · ${question.date} · ${question.account}", style = MaterialTheme.typography.bodySmall, color = MutedText)
            if (question.suggested.isNotEmpty()) {
                Text("Suggested from your past choices: ${question.suggested.joinToString()}", style = MaterialTheme.typography.bodySmall, color = LedgerGreenDark)
            }
            androidx.compose.foundation.layout.Box {
                OutlinedButton(enabled = enabled && question.choices.isNotEmpty(), onClick = { menuOpen = true }) {
                    Text(selected.ifBlank { "Choose a category" })
                }
                DropdownMenu(expanded = menuOpen, onDismissRequest = { menuOpen = false }) {
                    question.choices.forEach { choice ->
                        DropdownMenuItem(text = { Text(choice) }, onClick = { selected = choice; menuOpen = false })
                    }
                }
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(checked = always, onCheckedChange = { always = it }, enabled = enabled)
                Text("Use for future payments to this payee", style = MaterialTheme.typography.bodySmall)
            }
            Button(enabled = enabled && selected.isNotBlank(), onClick = { onApply(selected, always) }) {
                Text(if (always) "Save category and rule" else "Save category")
            }
        }
    }
}

@Composable
private fun SummaryCard(label: String, amountPaise: Long, modifier: Modifier = Modifier) {
    ElevatedCard(shape = RoundedCornerShape(20.dp), modifier = modifier) {
        Column(Modifier.padding(15.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Text(label, style = MaterialTheme.typography.labelMedium, color = MutedText)
            Text(formatInr(amountPaise), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = LedgerGreenDark)
        }
    }
}

@Composable
private fun TransactionCard(item: FinanceTransaction, expanded: Boolean = false) {
    ElevatedCard(shape = RoundedCornerShape(19.dp), modifier = Modifier.fillMaxWidth(), colors = CardDefaults.elevatedCardColors(containerColor = Color.White)) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 15.dp, vertical = 13.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(item.payee.ifBlank { item.description.ifBlank { "Ledger transaction" } }, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                Text("${item.date} · ${item.category.ifBlank { "Uncategorised" }}", style = MaterialTheme.typography.labelSmall, color = MutedText)
                if (expanded && item.description.isNotBlank() && item.description != item.payee) {
                    Text(item.description, style = MaterialTheme.typography.bodySmall, color = MutedText)
                    Text("${item.type.replace('_', ' ')} · ${item.source} → ${item.destination}", style = MaterialTheme.typography.labelSmall, color = MutedText)
                }
            }
            Text(formatInr(item.amountPaise), color = if (item.type == "deposit") LedgerGreen else Color(0xFF263A31), fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun GoalCard(goal: GoalProgress) {
    ElevatedCard(shape = RoundedCornerShape(20.dp), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(17.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(goal.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                Text("${goal.percent}%", color = LedgerGreen, fontWeight = FontWeight.Bold)
            }
            LinearProgressIndicator(progress = { (goal.percent.coerceIn(0, 100)) / 100f }, modifier = Modifier.fillMaxWidth(), color = LedgerGreen)
            Text("${formatInr(goal.savedPaise)} of ${formatInr(goal.targetPaise)}", style = MaterialTheme.typography.bodySmall)
            goal.neededPerMonthPaise?.let { Text("${formatInr(it)} per month needed${goal.targetDate?.let { d -> " · by $d" }.orEmpty()}", style = MaterialTheme.typography.labelSmall, color = MutedText) }
        }
    }
}

@Composable
private fun UpcomingCard(item: UpcomingItem) {
    ElevatedCard(shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 15.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(item.name.ifBlank { item.type.replace('_', ' ').replaceFirstChar { it.uppercase() } }, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                Text(item.date, style = MaterialTheme.typography.labelSmall, color = MutedText)
            }
            Text(formatInr(item.amountPaise), fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun AlertCard(alert: FinanceAlert, onReconnect: (String) -> Unit) {
    Surface(shape = RoundedCornerShape(16.dp), color = if (alert.severity == "high") Color(0xFFFFE9E4) else Color.White) {
        Row(Modifier.fillMaxWidth().padding(13.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("•", color = if (alert.severity == "high") Color(0xFFB43E2F) else AccentOrange, style = MaterialTheme.typography.titleLarge)
            Column(Modifier.weight(1f)) {
                Text(alert.message, modifier = Modifier.padding(start = 9.dp), style = MaterialTheme.typography.bodySmall)
                if (alert.link != null) {
                    TextButton(onClick = { onReconnect(alert.link) }) {
                        Text(if (alert.type == "google_reconnect") "Reconnect Google" else "Open link")
                    }
                }
            }
        }
    }
}

@Composable
private fun ReviewCard(item: ReviewMessage, enabled: Boolean, onLabel: (FeedbackType) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    ElevatedCard(shape = RoundedCornerShape(21.dp), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(item.sender.ifBlank { "Bank message" }, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                Surface(shape = RoundedCornerShape(40), color = Color(0xFFFFEAD8)) {
                    Text(item.reason.replace('_', ' '), modifier = Modifier.padding(horizontal = 9.dp, vertical = 5.dp), color = LedgerGreenDark, style = MaterialTheme.typography.labelSmall)
                }
            }
            Text(item.text.ifBlank { "Message text is unavailable" }, style = MaterialTheme.typography.bodyMedium, color = Color(0xFF35413A))
            Text(item.sentAt.take(16).replace('T', ' '), style = MaterialTheme.typography.labelSmall, color = MutedText)
            if (item.reason == "unparsed" || item.reason == "unknown_sender") {
                Button(enabled = enabled, onClick = { expanded = true }) { Text("Correct message type") }
                androidx.compose.material3.DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                    feedbackTypes.forEach { choice ->
                        androidx.compose.material3.DropdownMenuItem(text = { Text(choice.title) }, onClick = { expanded = false; onLabel(choice) })
                    }
                }
            } else {
                Text("This item needs a different review action.", style = MaterialTheme.typography.bodySmall, color = MutedText)
            }
        }
    }
}

@Composable
private fun ChatBubble(role: String, content: String) {
    val isUser = role == "user"
    Surface(
        shape = RoundedCornerShape(19.dp),
        color = if (isUser) LedgerGreen else Color.White,
        modifier = Modifier.fillMaxWidth(if (isUser) 0.88f else 1f).padding(start = if (isUser) 36.dp else 0.dp, end = if (isUser) 0.dp else 36.dp),
    ) {
        Text(content, modifier = Modifier.padding(14.dp), color = if (isUser) Color.White else Color(0xFF26352D), style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun SectionHeading(title: String, subtitle: String) {
    Row(Modifier.fillMaxWidth().padding(top = 4.dp, bottom = 2.dp), verticalAlignment = Alignment.Bottom) {
        Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
        Text(subtitle, style = MaterialTheme.typography.labelSmall, color = MutedText)
    }
}

@Composable
private fun EmptyCard(title: String, message: String) {
    ElevatedCard(shape = RoundedCornerShape(20.dp), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(17.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            Text(message, style = MaterialTheme.typography.bodySmall, color = MutedText)
        }
    }
}

@Composable
private fun LoadingCard() {
    Row(Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        androidx.compose.material3.CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
        Text("Loading from your private server…", style = MaterialTheme.typography.bodySmall, color = MutedText)
    }
}

private fun formatInr(paise: Long): String {
    val formatter = java.text.NumberFormat.getCurrencyInstance(Locale("en", "IN")).apply {
        currency = Currency.getInstance("INR")
        minimumFractionDigits = 2
        maximumFractionDigits = 2
    }
    return formatter.format(BigDecimal.valueOf(paise, 2))
}
