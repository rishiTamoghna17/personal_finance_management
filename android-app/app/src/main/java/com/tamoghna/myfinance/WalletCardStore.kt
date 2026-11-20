package com.tamoghna.myfinance

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Owner-added card display metadata; encrypted locally and never synced to the bridge. */
internal data class WalletCard(
    val id: String,
    val nickname: String,
    val issuer: String,
    val color: Long,
    val lastFour: String,
    val expiry: String,
    val balancePaise: Long,
    val linkedAccountId: String? = null,
)

internal class WalletCardStore(context: Context) {
    private val prefs = context.getSharedPreferences("private_wallet_cards", Context.MODE_PRIVATE)

    fun load(): List<WalletCard> = try {
        val raw = prefs.getString(DATA_KEY, null) ?: return emptyList()
        val packed = Base64.decode(raw, Base64.NO_WRAP)
        require(packed.size > IV_SIZE)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(TAG_BITS, packed, 0, IV_SIZE))
        val array = JSONArray(String(cipher.doFinal(packed.copyOfRange(IV_SIZE, packed.size)), Charsets.UTF_8))
        (0 until array.length()).map { i ->
            val item = array.getJSONObject(i)
            WalletCard(item.getString("id"), item.getString("nickname"), item.getString("issuer"), item.getLong("color"), item.getString("lastFour"), item.getString("expiry"), item.getLong("balancePaise"), item.optString("linkedAccountId").takeUnless { it.isBlank() || it == "null" })
        }
    } catch (_: Exception) { emptyList() }

    fun save(cards: List<WalletCard>) {
        val array = JSONArray()
        cards.forEach { c -> array.put(JSONObject().put("id", c.id).put("nickname", c.nickname).put("issuer", c.issuer).put("color", c.color).put("lastFour", c.lastFour).put("expiry", c.expiry).put("balancePaise", c.balancePaise).put("linkedAccountId", c.linkedAccountId)) }
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        val packed = cipher.iv + cipher.doFinal(array.toString().toByteArray(Charsets.UTF_8))
        check(prefs.edit().putString(DATA_KEY, Base64.encodeToString(packed, Base64.NO_WRAP)).commit()) { "Could not save the encrypted wallet" }
    }

    private fun secretKey(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true).build())
        }.generateKey()
    }

    private companion object {
        const val KEY_ALIAS = "my-finance-private-wallet"
        const val DATA_KEY = "encrypted_wallet_cards"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val IV_SIZE = 12
        const val TAG_BITS = 128
    }
}
