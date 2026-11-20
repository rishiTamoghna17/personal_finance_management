package com.tamoghna.myfinance

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class FinanceMessagingService : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        val credentials = BridgeCredentials(applicationContext)
        if (!credentials.hasToken()) return
        CoroutineScope(Dispatchers.IO).launch {
            runCatching { BridgeApi(credentials).registerPushToken(token) }
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val kind = message.data["kind"] ?: return
        val route = message.data["route"]?.takeIf { it == "review" } ?: "home"
        val body = when (kind) {
            "category_needed" -> "A payment needs a category. Open the app to review."
            "review_waiting" -> "An item needs your review. Open the app to see details."
            "reconnect_google" -> "A connected service needs attention. Open the app to reconnect."
            "due" -> "A finance reminder is ready. Open the app to review."
            "weekly_digest" -> "Your weekly finance summary is ready. Open the app to view it."
            else -> "A finance update is ready. Open the app to review."
        }
        createChannel()
        val openApp = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra(MainActivity.EXTRA_NOTIFICATION_ROUTE, route)
        }
        val pending = PendingIntent.getActivity(
            this, route.hashCode(), openApp,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle("My Finance")
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
            .setAutoCancel(true)
            .setContentIntent(pending)
            .build()
        if (Build.VERSION.SDK_INT < 33 || checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) == android.content.pm.PackageManager.PERMISSION_GRANTED) {
            NotificationManagerCompat.from(this).notify((System.currentTimeMillis() % Int.MAX_VALUE).toInt(), notification)
        }
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "Finance updates", NotificationManager.IMPORTANCE_DEFAULT).apply {
                    description = "Private reminders from My Finance"
                    lockscreenVisibility = android.app.Notification.VISIBILITY_PRIVATE
                },
            )
        }
    }

    private companion object { const val CHANNEL_ID = "finance_updates" }
}
