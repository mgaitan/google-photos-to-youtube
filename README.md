[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mgaitan/google-photos-to-youtube/blob/main/google_photos_to_youtube.ipynb)

Google Photos is expensive and YouTube is free. Why not move my videos there (using their bandwidth and resources for more pleasure)?

## How it works

It searches for videos using the Google Photos API in your account and displays a thumbnail of each one. Then you can complete some metadata and upload it to the same or different YouTube account.
The uploading process is done in chunks, so it doesn't require downloading the full video to start uploading it.


## Setup

1. Follow https://developers.google.com/photos/library/guides/get-started to create a new project (a "Desktop app" could work). Remember to copy the `CLIENT_ID` and `CLIENT_SECRET` of your app.

2. **Important**: Configure OAuth redirect URIs. In your Google Cloud Console:
   - Go to APIs & Services > Credentials
   - Click on your OAuth 2.0 Client ID
   - Under "Authorized redirect URIs", add these URIs:
     - `http://localhost:8080`
     - `http://127.0.0.1:8080`
     - `http://localhost:8081`
     - `http://localhost:8082`

3. In addition to Google Photos, your app requires access to the `YouTube Data v3 API`. Enable it from https://console.cloud.google.com/apis/dashboard by clicking "Enable APIS and SERVICES".

4. As your app will be in "Testing" mode, you need to authorize the specific accounts that will use the app. Go to https://console.cloud.google.com/apis/credentials/consent and add them by clicking "Add user". It could be more than one account, as the source Google Photos account and the YouTube account could be different.

5. Open [the notebook](https://colab.research.google.com/github/mgaitan/google-photos-to-youtube/blob/main/google_photos_to_youtube.ipynb) in Colab, run the cells and follow the instructions.

## What's New

- **Fixed OAuth Flow**: Replaced the deprecated Out-of-Band (OOB) OAuth flow with a modern local server-based approach
- **Automatic Browser Opening**: The authentication process now automatically opens your browser when possible
- **Better Error Handling**: More informative error messages and fallback options
- **Port Auto-detection**: Automatically finds an available port for the OAuth callback
