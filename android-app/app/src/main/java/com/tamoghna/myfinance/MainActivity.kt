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
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

private val LedgerGreen = Color(0xFF176B4D)
private val LedgerGreenDark = Color(0xFF104B38)
private val WarmCanvas = Color(0xFFF7F6F1)
private val AccentOrange = Color(0xFFE87722)

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
            ) {
                FeedbackHome(credentials)
            }
        }
    }
}

private data class ReviewMessage(
    val id: Int,
    val reason: String,
    val sender: String,
    val text: String,
    val sentAt: String,
)

private data class FeedbackType(val code: String, val title: String)

private val feedbackTypes = listOf(
    FeedbackType("transaction_alert", "Transaction alert"),
    FeedbackType("promotion", "Promotion"),
    FeedbackType("card_bill_payment", "Card bill payment"),
    FeedbackType("failed_payment", "Failed payment"),
    FeedbackType("refund_reversal", "Refund or reversal"),
    FeedbackType("due_reminder", "Due reminder"),
    FeedbackType("other", "Other"),
)

@Composable
private fun FeedbackHome(credentials: BridgeCredentials) {
    val scope = rememberCoroutineScope()
    val reviews = remember { mutableStateListOf<ReviewMessage>() }
    var server by remember { mutableStateOf(credentials.serverUrl()) }
    var tokenInput by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("Connect to your private finance server.") }
    var busy by remember { mutableStateOf(false) }

    fun launchRequest(request: suspend () -> String) {
        if (busy) return
        busy = true
        scope.launch {
            status = try {
                withContext(Dispatchers.IO) { request() }
            } catch (e: Exception) {
                "Could not reach the server: ${e.message ?: "connection failed"}"
            } finally {
                busy = false
            }
        }
    }

    fun refresh() = launchRequest {
        val items = BridgeApi(credentials).reviews()
        withContext(Dispatchers.Main) {
            reviews.clear()
            reviews.addAll(items)
        }
        "${items.size} item${if (items.size == 1) "" else "s"} waiting for review"
    }

    Scaffold(containerColor = WarmCanvas) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = 20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item {
                Column(modifier = Modifier.padding(top = 18.dp, bottom = 4.dp)) {
                    Text("MY FINANCE", style = MaterialTheme.typography.labelLarge, color = LedgerGreen, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(6.dp))
                    Text("Your money,\nin one place.", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold, color = LedgerGreenDark)
                    Spacer(Modifier.height(8.dp))
                    Text("Private finance overview and bank-message review", style = MaterialTheme.typography.bodyMedium, color = Color(0xFF58645E))
                }
            }
            item {
                ElevatedCard(
                    shape = RoundedCornerShape(24.dp),
                    colors = CardDefaults.elevatedCardColors(containerColor = Color.White),
                    elevation = CardDefaults.elevatedCardElevation(defaultElevation = 2.dp),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("Server connection", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                            Surface(shape = RoundedCornerShape(50), color = Color(0xFFE7F2EA)) {
                                Text("PRIVATE", modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp), color = LedgerGreen, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                            }
                        }
                        OutlinedTextField(
                            value = server,
                            onValueChange = { server = it },
                            label = { Text("Tailscale server URL") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                        )
                        OutlinedTextField(
                            value = tokenInput,
                            onValueChange = { tokenInput = it },
                            label = { Text("Bridge API token") },
                            placeholder = { Text(if (credentials.hasToken()) "Saved securely on this phone" else "Paste your token") },
                            singleLine = true,
                            visualTransformation = PasswordVisualTransformation(),
                            modifier = Modifier.fillMaxWidth(),
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            OutlinedButton(onClick = {
                                val cleaned = server.trim().trimEnd('/')
                                if (!cleaned.startsWith("https://")) {
                                    status = "Use the private HTTPS address beginning with https://"
                                } else if (tokenInput.isBlank() && !credentials.hasToken()) {
                                    status = "Paste your bridge API token first"
                                } else {
                                    credentials.setServerUrl(cleaned)
                                    if (tokenInput.isNotBlank()) credentials.saveToken(tokenInput.trim())
                                    tokenInput = ""
                                    status = "Connection details saved securely on this phone"
                                }
                            }) { Text("Save securely") }
                            Button(enabled = !busy, onClick = { refresh() }) { Text(if (busy) "Loading…" else "Load reviews") }
                        }
                        Text(status, style = MaterialTheme.typography.bodySmall, color = Color(0xFF58645E))
                    }
                }
            }
            item {
                Row(verticalAlignment = Alignment.Bottom, modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Review inbox", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                        Text("Your labels help recognize similar messages later.", style = MaterialTheme.typography.bodySmall, color = Color(0xFF58645E))
                    }
                    Surface(shape = RoundedCornerShape(14.dp), color = Color(0xFFFFEAD8)) {
                        Text("${reviews.size}", modifier = Modifier.padding(horizontal = 13.dp, vertical = 7.dp), color = LedgerGreenDark, fontWeight = FontWeight.Bold)
                    }
                }
            }
            if (reviews.isEmpty()) {
                item {
                    ElevatedCard(shape = RoundedCornerShape(20.dp), modifier = Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(18.dp)) {
                            Text("Nothing loaded yet", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                            Text("Connect to the server to see messages that need your review.", modifier = Modifier.padding(top = 5.dp), color = Color(0xFF58645E))
                        }
                    }
                }
            } else {
                items(reviews, key = { it.id }) { item ->
                    ReviewCard(item = item, enabled = !busy, onLabel = { label ->
                        launchRequest {
                            BridgeApi(credentials).label(item.id, label.code)
                            val updated = BridgeApi(credentials).reviews()
                            withContext(Dispatchers.Main) {
                                reviews.clear()
                                reviews.addAll(updated)
                            }
                            "Saved your correction: ${label.title}"
                        }
                    })
                }
            }
            item { Spacer(Modifier.height(12.dp)) }
        }
    }
}

@Composable
private fun ReviewCard(item: ReviewMessage, enabled: Boolean, onLabel: (FeedbackType) -> Unit) {
    ElevatedCard(
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.elevatedCardColors(containerColor = Color.White),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(item.sender.ifBlank { "Bank message" }, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                Surface(shape = RoundedCornerShape(50), color = Color(0xFFFFEAD8)) {
                    Text(item.reason.replace('_', ' '), modifier = Modifier.padding(horizontal = 9.dp, vertical = 5.dp), color = LedgerGreenDark, style = MaterialTheme.typography.labelSmall)
                }
            }
            Text(item.text.ifBlank { "Message text is unavailable" }, style = MaterialTheme.typography.bodyMedium, color = Color(0xFF35413A))
            Text(item.sentAt.take(16).replace('T', ' '), style = MaterialTheme.typography.labelSmall, color = Color(0xFF758078))
            if (item.reason == "unparsed" || item.reason == "unknown_sender") {
                FeedbackMenu(enabled = enabled, onLabel = onLabel)
            } else {
                Text("This review needs a different action in the finance app.", style = MaterialTheme.typography.bodySmall, color = Color(0xFF758078))
            }
        }
    }
}

@Composable
private fun FeedbackMenu(enabled: Boolean, onLabel: (FeedbackType) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        Button(enabled = enabled, onClick = { expanded = true }) { Text("Correct message type") }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            feedbackTypes.forEach { choice ->
                DropdownMenuItem(
                    text = { Text(choice.title) },
                    onClick = { expanded = false; onLabel(choice) },
                )
            }
        }
    }
}

private class BridgeApi(private val credentials: BridgeCredentials) {
    suspend fun reviews(): List<ReviewMessage> = withContext(Dispatchers.IO) {
        val response = request("GET", "/api/v1/review")
        val rows = response.getJSONArray("items")
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

    suspend fun label(id: Int, label: String) = withContext(Dispatchers.IO) {
        request("POST", "/api/v1/review/$id/feedback", JSONObject().put("label", label))
    }

    private fun request(method: String, path: String, body: JSONObject? = null): JSONObject {
        val token = credentials.readToken().ifBlank { error("Save the bridge API token first") }
        val base = credentials.serverUrl().trim().trimEnd('/')
        require(base.startsWith("https://")) { "The server address must use private HTTPS" }
        val connection = (URL(base + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 12_000
            readTimeout = 20_000
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
            if (code !in 200..299) error("Server returned HTTP $code")
            return JSONObject(content)
        } finally {
            connection.disconnect()
        }
    }
}
