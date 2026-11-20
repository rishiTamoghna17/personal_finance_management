package com.tamoghna.myfinance

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Stores the bridge bearer token encrypted with a non-exportable Android Keystore key. */
internal class BridgeCredentials(context: Context) {
    private val prefs = context.getSharedPreferences("my_finance_credentials", Context.MODE_PRIVATE)

    fun serverUrl(): String = prefs.getString(KEY_SERVER, DEFAULT_SERVER) ?: DEFAULT_SERVER

    fun setServerUrl(value: String) {
        prefs.edit().putString(KEY_SERVER, value.trim().trimEnd('/')).apply()
    }

    fun hasToken(): Boolean = prefs.contains(KEY_TOKEN)

    fun saveToken(token: String) {
        require(token.isNotBlank()) { "Token cannot be empty" }
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        val encrypted = cipher.doFinal(token.toByteArray(Charsets.UTF_8))
        val packed = cipher.iv + encrypted
        check(prefs.edit().putString(KEY_TOKEN, Base64.encodeToString(packed, Base64.NO_WRAP)).commit()) {
            "Could not save the encrypted token"
        }
    }

    fun readToken(): String {
        val packed = prefs.getString(KEY_TOKEN, null)?.let { Base64.decode(it, Base64.NO_WRAP) } ?: return ""
        require(packed.size > GCM_IV_BYTES) { "Saved token data is invalid" }
        val iv = packed.copyOfRange(0, GCM_IV_BYTES)
        val encrypted = packed.copyOfRange(GCM_IV_BYTES, packed.size)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(GCM_TAG_BITS, iv))
        return String(cipher.doFinal(encrypted), Charsets.UTF_8)
    }

    private fun secretKey(): SecretKey {
        val store = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        (store.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }

        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build(),
        )
        return generator.generateKey()
    }

    private companion object {
        const val DEFAULT_SERVER = "https://finance.tail1cee0a.ts.net"
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val KEY_ALIAS = "my-finance-bridge-token"
        const val KEY_SERVER = "server_url"
        const val KEY_TOKEN = "encrypted_bridge_token"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val GCM_IV_BYTES = 12
        const val GCM_TAG_BITS = 128
    }
}
