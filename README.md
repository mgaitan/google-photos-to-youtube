[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mgaitan/google-photos-to-youtube/blob/main/google_photos_to_youtube.ipynb)

Google Photos is expensive and Youtube is free. Why not move my videos there (using their bandwidth and resources for more pleasure)?

## How it works

It searches videos using the Google Photos api in your account and display a thumbnail of each one. Then you can complete some metadata and upload it to the same or different Youtube account. 
The uploading process is done in chunks, so it doesn't require to download the full video to start uploading it. 


## Setup

1. Copy `client_id.json.dist` as `client_id.json`

and follow https://developers.google.com/photos/library/guides/get-started to create a new project. 

It requires permissions on Google Photos and Youtube data v3 APIs to download and upload from one service to the other. 

2. Replace `YOUR_CLIENT_ID` and `YOUR_CLIENT_SECRET` in the client_id.json file with the provided Client ID. 

3. As your app will be in "Testing" mode, you need to authorize the specific accounts that will use the app. Goto to https://console.cloud.google.com/apis/credentials/consent and add them clicking in "+ Add user".

3. Open the notebook in Colab and upload `client_id.json`. Then run the cells and follow the instructions. 


