# OAuth Redirect URIs Setup Guide

Use this guide to update your developer dashboard settings for Spotify, Google, Microsoft, and Notion to resolve authorization and redirect mismatch errors.

Depending on the service, you will use one of these two redirect URLs:
*   **Spotify**: `http://127.0.0.1:5000/oauth/callback`
*   **Google, Microsoft, Notion, Slack**: `http://localhost:5000/oauth/callback`

---

## 1. 🟢 Spotify (`redirect_uri: Not matching configuration` / `This redirect URI is not secure`)
Spotify's developer portal flags `http://localhost` as insecure for non-HTTPS connections, but permits `http://127.0.0.1` as a secure local loopback.
1. Open the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Click on your registered App and go to **Settings**.
3. Under **Redirect URIs**, add exactly:
   ```text
   http://127.0.0.1:5000/oauth/callback
   ```
4. Save the configuration.

---

## 2. 🔵 Google (`Error 400: redirect_uri_mismatch`, `Invalid Redirect: cannot contain whitespace`, or `Error 403: access_denied`)
Google Cloud restricts OAuth callback endpoints and controls application authorization via the OAuth Consent Screen configuration.

### A. Fixing `Error 400: redirect_uri_mismatch` or `Invalid Redirect`
1. Open the [Google Cloud Console Credentials Page](https://console.cloud.google.com/apis/credentials).
2. Under **OAuth 2.0 Client IDs**, select the client credential you created.
3. Scroll to the **Authorized redirect URIs** section.
4. Click **Add URI** and enter:
   ```text
   http://localhost:5000/oauth/callback
   ```
   > [!IMPORTANT]
   > Make sure there are no leading or trailing spaces (whitespaces) when copying and pasting the URL, otherwise Google Cloud Console will show the error: `"Invalid Redirect: cannot contain whitespace."`
5. Click **Save** at the bottom.

### B. Fixing `Error 403: access_denied` (Thing has not completed the Google verification process)
Because the app is in **Testing** status and has not been verified by Google, Google only allows access to explicitly registered developer accounts.
1. Open the [Google Cloud Console OAuth Consent Screen Page](https://console.cloud.google.com/apis/credentials/consent).
2. Ensure your user type / publishing status is set to **Testing**.
3. Scroll down to the **Test users** section.
4. Click **Add Users**.
5. Enter the exact email address you are trying to log in with (e.g., `240714100093@centurionuniv.edu.in`).
6. Click **Save** to apply the changes.

---

## 3. 🔴 Microsoft (`unauthorized_client: The client does not exist...` or `Must start with "HTTPS" or "http://localhost"`)
This error occurs because Microsoft Azure Portal restricts local HTTP callback URLs. It strictly requires the callback URL to start with `https://` or `http://localhost` (IP addresses like `127.0.0.1` are not allowed).

1. Log in to [Azure Portal App Registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade).
2. Open your Registered App.
3. Under the **Authentication** blade:
   - Click **Add a platform** -> **Web** (or edit existing Web URIs) and add exactly:
     ```text
     http://localhost:5000/oauth/callback
     ```
   - Scroll down to the **Supported account types** section. Change the option to:
     * **"Accounts in any organizational directory (Any Microsoft Entra ID tenant - Multitenant) and personal Microsoft accounts (e.g. Skype, Xbox)"**
4. Save your changes.

---

## 4. 🟤 Notion (`Missing or invalid redirect_uri` or `HTTPS requirements`)
Notion integrations require explicit registration of callback redirects. Notion allows `http://localhost` for local development, but rejects IP addresses like `127.0.0.1` as public/private IPs.

1. Open the [Notion Integrations Page](https://www.notion.so/profile/integrations).
2. Select your integration.
3. Under the **Redirect URIs** field, enter exactly:
   ```text
   http://localhost:5000/oauth/callback
   ```
   > [!WARNING]
   > Do **NOT** prepend `https://` to form something like `https://http://127.0.0.1:5000/oauth/callback` or `https://http://localhost:5000/oauth/callback`. Notion allows `http://localhost` for local development without any prefix/suffix modification.
4. Click **Save Changes**.
